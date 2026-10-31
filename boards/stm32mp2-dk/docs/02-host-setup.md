# 02 · Host setup

What you need on your PC, how to check it, and what a build costs.

## What kind of PC

| Host | Works? | Notes |
| --- | --- | --- |
| Ubuntu 24.04 / Debian 13, x86-64 | yes | the reference. The scripts download the x86-64 Arm toolchains. |
| Ubuntu 24.04 / Debian 13, ARM64 (Ampere server, Linux VM on an Apple-silicon Mac, …) | yes | the scripts download the ARM64-hosted Arm toolchains. **This is the host the board was built and checked on**, in a container. |
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
| U-Boot and TF-A host tools | `libgnutls28-dev uuid-dev python3 python3-dev python3-setuptools python3-pyelftools swig device-tree-compiler` |
| OP-TEE's SCMI server | `cmake` (OP-TEE runs it on the SCP-firmware sources to generate a module list) |
| kernel install, unpacking | `kmod cpio rsync xz-utils zstd` |
| downloads | `wget ca-certificates` |
| rootless SD image | `fakeroot e2fsprogs fdisk bmap-tools openssl` |
| Debian root filesystem | `mmdebstrap qemu-user-static binfmt-support uidmap` |
| faster rebuilds | `ccache` |
| `-s st` only | `python3-pil python3-cryptography` (OP-TEE 4.0 renders a font and signs its trusted applications; `./build.sh -s st deps --install` adds them) |

`qemu-user-static` is only needed on an x86 PC: the Debian packages are for arm64, and their post-install
scripts must *run*; qemu runs them. On an ARM64 PC they run natively.

## Disk, RAM, time

Measured on an ARM64 Ubuntu 24.04 container (11 cores shared with another job, 7.6 GB RAM):

| Item | Size / time |
| --- | --- |
| `build/downloads` (toolchain tarballs, kernel tarball, Alpine) | about 0.4 GB (the second toolchain is fetched once) |
| `build/toolchain` (two Arm toolchains, unpacked) | 1.3 GB |
| `build/src` (TF-A, OP-TEE, SCP-firmware, U-Boot, DDR firmware, kernel tree) | 2.9 GB before the kernel build, more after |
| `build/deploy` | 0.3 GB for the firmware and rootfs; the kernel overlay is 0.1 GB (Image 41 MB, modules 80 MB) and its tarball 35 MB; the Debian SD image is 1.1 GB apparent (0.4 GB on disk, it is sparse) |
| `./build.sh firmware` from an empty `build/` (toolchain download included, 6 jobs) | about 2 minutes |
| `./build.sh kernel` (first time) | 36 minutes, 6 jobs; later builds seconds to minutes ([04](04-kernel.md)). This is the long step |
| `./build.sh rootfs` (Debian trixie) | about 3 minutes |
| `-s st`: `build/src-st` (TF-A, OP-TEE, U-Boot, ST's device trees, DDR firmware, ST's kernel tree) | 3.7 GB after the kernel build (the kernel tree alone 3.4 GB); `work-st` 0.5 GB; `deploy-st` 0.2 GB with the Alpine image; downloads and toolchains are shared with the mainline stack |
| `-s st`: `./build.sh -s st firmware` from empty source directories (toolchains already there, 4 jobs) | under 2 minutes |
| `-s st`: `./build.sh -s st kernel` (first time) | about 25 minutes, 4 jobs |

`./build.sh all` checks for 15 GB free before it starts. To build on another disk, put
`BUILD_DIR=/mnt/big/stm32mp2` into `config/local.conf`.

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
   `rootfs` step (or use Alpine).

```bash
# once: an Ubuntu 24.04 image with the build dependencies
cat > Dockerfile <<'EOF'
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential git make bc bison flex libssl-dev libncurses-dev libelf-dev cmake \
      libgnutls28-dev uuid-dev python3 python3-dev python3-setuptools python3-pyelftools swig \
      device-tree-compiler kmod cpio rsync xz-utils zstd wget ca-certificates fakeroot \
      e2fsprogs fdisk bmap-tools openssl mmdebstrap uidmap ccache sudo python3-pil python3-cryptography \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m -s /bin/bash dev
USER dev
EOF
docker build -t mp2-build .
docker volume create mp2-build-data

# every time: the repository is mounted, the build output lives in the volume
docker run --rm -it -v "$PWD":/w -w /w -v mp2-build-data:/build -e BUILD_DIR=/build mp2-build \
  ./build.sh firmware
```

To copy the result out of the volume:

```bash
docker run --rm -v mp2-build-data:/build -v "$PWD":/out mp2-build cp /build/deploy/sdcard.img /out/
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
