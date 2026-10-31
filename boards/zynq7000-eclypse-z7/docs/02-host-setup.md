# 02 · Host setup

What you need on your PC, how to check it, and what a build costs.

## What kind of PC

| Host | Works? | Notes |
| --- | --- | --- |
| Ubuntu 24.04 / Debian 13, x86-64 | yes | the reference for users. The scripts download the x86-64 Arm toolchain (URL and sha256 checked, not run). |
| Ubuntu 24.04 / Debian 13, ARM64 (Ampere server, Linux VM on an Apple-silicon Mac, …) | yes | the scripts download the ARM64-hosted toolchain. **This is the host the board was built and checked on**, in a container. |
| macOS, Windows | via a Linux container or VM | see [below](#using-a-container-on-macos-or-windows). Do not build the kernel on a case-insensitive disk. |
| Other Linux | probably | `./build.sh deps` only knows apt package names; install the equivalents. |

You do **not** need Vivado, Vitis or PetaLinux, and no cross-compiler from your distribution: the build
downloads the exact one it was tested with (`TOOLCHAIN=arm`, the default).

## Check and install the packages

```bash
./build.sh deps              # lists what is missing
./build.sh deps --install    # apt-get installs it (asks for sudo)
```

The list is `HOST_PACKAGES` in [`build.sh`](../build.sh). In short:

| For | Packages |
| --- | --- |
| compiling everything | `build-essential git make bc bison flex libssl-dev libncurses-dev libelf-dev` |
| U-Boot host tools | `libgnutls28-dev uuid-dev python3 python3-dev python3-setuptools python3-pyelftools swig device-tree-compiler` |
| kernel install, unpacking | `kmod cpio rsync xz-utils zstd` |
| downloads | `wget ca-certificates` |
| rootless SD image | `fakeroot e2fsprogs fdisk dosfstools mtools bmap-tools openssl` |
| Debian root filesystem | `mmdebstrap arch-test qemu-user-static binfmt-support uidmap` |
| faster rebuilds | `ccache` |

`qemu-user-static` is needed to build the **Debian** root filesystem on **every** PC that is not 32-bit ARM,
**including an ARM64 PC**: the packages are 32-bit `armhf`, their post-install scripts must *run*, and most
64-bit Arm CPUs (Apple silicon, Ampere, most servers) cannot execute 32-bit code. qemu runs the scripts. The
Alpine root filesystem is a plain download and needs none of this.

## Disk, RAM, time

Measured on an ARM64 Ubuntu 24.04 container (4 build jobs, 7.6 GB RAM shared with other work):

| Item | Size / time |
| --- | --- |
| `build/downloads` (toolchain, kernel tarball, Alpine, the PS7 hardware-design file) | about 0.5 GB |
| `build/toolchain` (one Arm toolchain, unpacked) | 0.9 GB |
| `build/src` (U-Boot checkout, kernel tree, before building) | 1.5 GB; the kernel tree grows to ~12 GB once built with `multi_v7_defconfig` (it builds drivers for dozens of SoCs) |
| `build/deploy` | BOOT.BIN 131,676 bytes, u-boot.img 1.1 MB, zImage + modules, the rootfs tarball (Debian armhf 266 MB, Alpine 5.5 MB) and the image |
| `./build.sh uboot` from an empty `build/` (toolchain download included, 4 jobs) | about 3 minutes |
| `./build.sh kernel` the first time | **the long step**: see the status table in the [README](../README.md) for the measured time |
| `./build.sh -r alpine rootfs` | seconds |
| `./build.sh rootfs` (Debian, qemu-emulated) | about 6 minutes |
| `./build.sh image` | well under a minute |

Make sure `build/` has **15 GB** free (`check_disk_space` asks before `all`). Put it on another disk with
`BUILD_DIR=/mnt/big/build` in `config/local.conf`.

## Using a container on macOS or Windows

The scripts are plain bash for Debian/Ubuntu, so any Ubuntu 24.04 container works. The two things that bite:

* **Use a Linux file system for `build/`** (a Docker volume, or the container's own disk), not a bind-mounted
  macOS folder: the kernel tree has file names that differ only in letter case, and bind mounts are slow.
* **qemu for Debian.** Docker Desktop registers qemu handlers for foreign architectures in its VM, but a container
  does not see `binfmt_misc` unless it is started `--privileged` and the file system is mounted:

  ```bash
  docker run --rm -it --privileged -v zynq-build:/work ubuntu:24.04 bash
  mount -t binfmt_misc none /proc/sys/fs/binfmt_misc      # if /proc/sys/fs/binfmt_misc is empty
  ```

  The script accepts any `binfmt_misc` entry that handles 32-bit ARM ELF files (the name is `qemu-arm` with
  Debian's packages, `arm` with Docker Desktop).
* `mmdebstrap` runs rootless in a user namespace; in a container that needs `--privileged` (or `--cap-add` +
  `--security-opt`), otherwise the script falls back to `sudo`.

## Writing the SD card

You need a card reader and a microSD card of **8 GB or more**. Everything on the card is erased. The
BootROM reads a FAT16/FAT32 partition and the one on this card is only 300 MiB, so the card size does not
matter to it; the root partition can later be grown to the whole card (`--expand`).

Continue with [03 · U-Boot SPL](03-uboot-spl.md).
