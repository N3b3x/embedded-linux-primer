# 02 · Host setup

What you need on your PC, how to check it, and what a build costs.

## What kind of PC

| Host | Works? | Notes |
| --- | --- | --- |
| Ubuntu 24.04 / Debian 13, x86-64 | yes | the reference. The scripts download the x86-64 Arm toolchains. |
| Ubuntu 24.04 / Debian 13, ARM64 (Ampere server, Linux VM on an Apple-silicon Mac, …) | yes | the scripts download the ARM64-hosted Arm toolchains. **This is the host the board was built and checked on**, in a container. The Debian root filesystem needs `qemu-user-static` here too (see below). |
| macOS, Windows | via a Linux container or VM | see [below](#using-a-container-on-macos-or-windows). Do not build the kernel on a case-insensitive disk. |
| Other Linux | probably | `./build.sh deps` only knows apt package names; install the equivalents. |

You do **not** need a cross-compiler from your distribution: the build downloads the exact one it was
tested with (`TOOLCHAIN=arm`, the default).

## Check and install the packages

```bash
./build.sh deps              # lists what is missing
./build.sh deps --install    # apt-get installs it (asks for sudo)
```

The list is `HOST_PACKAGES` in [`build.sh`](../build.sh). In short:

| For | Packages |
| --- | --- |
| compiling everything | `build-essential git make bc bison flex libssl-dev libncurses-dev libelf-dev` |
| U-Boot, TF-A and OP-TEE host tools | `libgnutls28-dev uuid-dev python3 python3-dev python3-setuptools python3-pyelftools swig device-tree-compiler` |
| kernel install, unpacking | `kmod cpio rsync xz-utils zstd` |
| downloads | `wget ca-certificates` |
| rootless SD image | `fakeroot e2fsprogs fdisk bmap-tools openssl` |
| Debian root filesystem | `mmdebstrap arch-test qemu-user-static binfmt-support uidmap` |
| faster rebuilds | `ccache` |

`qemu-user-static` is needed on **every** PC except a 32-bit ARM one: the Debian packages are for `armhf`
(32-bit ARM), and their post-install scripts must *run*; qemu runs them. This is different from the 64-bit
STM32MP2 board, where an ARM64 PC can run the target's programs natively: many ARM64 CPUs (Apple silicon among
them) cannot execute 32-bit ARM code at all.

## Disk, RAM, time

Measured on an ARM64 Ubuntu 24.04 container (shared with other jobs, 7.6 GB RAM, 4 build jobs):

| Item | Size / time |
| --- | --- |
| `build/downloads` (two toolchain tarballs, kernel tarball, Alpine, Debian keyring) | 0.4 GB |
| `build/toolchain` (two Arm toolchains, unpacked) | 1.6 GB |
| `build/src` (TF-A, OP-TEE, U-Boot, kernel tree; the kernel tree is 3.3 GB after the build) | 3.8 GB |
| `build/work` + `build/deploy` | 0.55 GB + 0.64 GB (Debian rootfs tar 266 MiB, kernel overlay and its tarball 22 MB, firmware 3 MB) |
| the Debian SD image | 958 MiB apparent, 300 MB on disk (it is sparse) |
| `./build.sh firmware` from an empty `build/` (toolchain download included, 4 jobs) | 2.5 minutes |
| `./build.sh kernel` (first time) | **24 min 41 s**, 4 jobs. This is the long step; a rebuild took 88 s ([04](04-kernel.md)) |
| `./build.sh rootfs` (Debian trixie `armhf`, under QEMU) | 228 s |
| `./build.sh image` | 21 s |

`./build.sh all` checks for 15 GB free before it starts. To build on another disk, put
`BUILD_DIR=/mnt/big/stm32mp1` into `config/local.conf`.

## Rootless Debian and the Ubuntu 24.04 user-namespace rule

The Debian root filesystem is made by `mmdebstrap`, which can run without root by using a *user namespace*.
`scripts/rootfs.sh` tries that first (`mmdebstrap --mode=unshare`) and falls back to `sudo`.

Ubuntu 24.04 restricts unprivileged user namespaces by default. If rootless mode fails with a permission
error, either let the script use `sudo` (it does automatically when it cannot use the namespace), or relax
the rule once:

```bash
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
```

Alpine ([05](05-rootfs.md)) needs neither.

## Using a container on macOS or Windows

This is the setup the scripts were exercised in. Two rules matter:

1. The kernel source contains files whose names differ only by letter case. On a case-insensitive disk
   (the macOS and Windows default) they overwrite each other. Keep `build/` on a **Docker volume**, not on a
   mounted host folder.
2. mmdebstrap's rootless mode needs extra privileges inside Docker: add `--privileged` for the
   `rootfs` step (or use Alpine). On Docker Desktop for an Apple-silicon Mac the Docker VM already has a binfmt handler for 32-bit ARM
   (named `arm`, backed by QEMU; checked here with `docker run --platform linux/arm/v7 debian:trixie-slim uname -m`
   printing `armv7l`), so nothing needs installing inside the container.

```bash
# once: an Ubuntu 24.04 image with the build dependencies
cat > Dockerfile <<'EOF'
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential git make bc bison flex libssl-dev libncurses-dev libelf-dev \
      libgnutls28-dev uuid-dev python3 python3-dev python3-setuptools python3-pyelftools swig \
      device-tree-compiler kmod cpio rsync xz-utils zstd wget ca-certificates fakeroot \
      e2fsprogs fdisk bmap-tools openssl mmdebstrap arch-test qemu-user-static binfmt-support uidmap ccache sudo \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m -s /bin/bash dev
USER dev
EOF
docker build -t mp1-build .
docker volume create mp1-build-data

# every time: the repository is mounted, the build output lives in the volume
docker run --rm -it -v "$PWD":/w -w /w -v mp1-build-data:/build -e BUILD_DIR=/build mp1-build \
  ./build.sh firmware
```

To copy the result out of the volume:

```bash
docker run --rm -v mp1-build-data:/build -v "$PWD":/out mp1-build cp /build/deploy/sdcard.img /out/
```

Writing the card is the one step that must run on a machine that can see the card reader: use
`./build.sh flash` there, or `bmaptool`/`dd`/balenaEtcher on the host ([07](07-flashing-and-booting.md)).

## Serial console

You need a way to see the board's serial console. The DK's debug USB connector is wired to an on-board
ST-LINK that presents a virtual serial port to your PC (which connector: [12 · Board tour](12-board-tour.md)).
On Linux it is usually `/dev/ttyACM0` (check with `dmesg` after plugging it in); any terminal program works:

```bash
sudo apt install picocom
picocom -b 115200 /dev/ttyACM0       # leave with Ctrl-A then Ctrl-X
```

Next: [03 · Firmware and U-Boot](03-firmware-and-uboot.md).
