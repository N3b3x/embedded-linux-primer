# 02 · Host setup

[Docs](README.md) › **02 · Host setup**

What you need on your desk and on your PC, and how to check it before you start a two-hour job.

## 1. The PC

| Need | Why |
| --- | --- |
| **x86-64 Linux, Ubuntu 22.04** (NVIDIA's Quick Start names 20.04 and 22.04) | NVIDIA's flash tools are x86-64 programs and so is its reference cross compiler. The scripts refuse to run elsewhere |
| 8 GB RAM or more | the kernel build, and an NFS export of a multi-GB image |
| about 40-60 GB free disk | our estimate, not an NVIDIA figure: 2.6 GB of downloads (plus 370 MB for your own kernel), the unpacked rootfs, the kernel build tree and the generated flash images each take several GB. `./build.sh all` warns below 60 GB |
| `sudo` | the root filesystem must be created with root ownership; the flash tool installs temporary `udev` rules and an NFS export |
| **IPv6 enabled**, no firewall blocking SSH/NFS on the USB link | NVIDIA's tool talks to the board over IPv6 (`fc00:1:1::/48` and `fe80::`) |
| Internet access | NVIDIA's download servers (`developer.nvidia.com`, redirecting to `developer.download.nvidia.com`) |

**macOS, Windows and ARM64 PCs cannot run the build or the flash.** `./build.sh` stops with a
message. You can still read every step on any machine with bash 4+: `./build.sh --dry-run all`.

**Virtual machines.** The board re-enumerates on USB during the flash (it first appears as the NVIDIA
recovery device, later as a USB Ethernet device). A VM's USB passthrough has to follow it. If the flash
stalls after step 2 ([11](11-recovery-and-usb-flash.md)), try a physical machine.

**Emulation is not good enough.** Running the x86-64 toolchain under QEMU or Rosetta on an ARM Mac got through about 1,800 compile
steps and then died with `Illegal instruction`. Use a real x86-64 machine for the kernel build.

**Case-insensitive file systems break the kernel unpack.** The Linux source tree contains files whose
names differ only in case. On macOS or Windows folders (including Docker bind mounts from them),
`tar` fails with `Directory renamed before its status could be extracted`. Build on a Linux filesystem.

## 2. The kit and the cables

| Item | Notes |
| --- | --- |
| Jetson Orin Nano Developer Kit | module P3767 on the P3768 carrier, with its power supply |
| **USB-C cable to the PC** | NVIDIA warns that a low-quality cable can make flashing fail. Connect the kit's USB-C port to the PC, preferably directly |
| **A jumper** for the 12-pin button header | to short the **REC** and **GND** pins: Force Recovery Mode ([11](11-recovery-and-usb-flash.md)) |
| Root storage: **one of** a microSD card (64 GB or larger), an NVMe M.2 SSD in the carrier's slot, a USB drive | NVIDIA states the size rule for SD cards and USB drives on Orin NX and Orin Nano |
| A DisplayPort monitor and a USB keyboard | optional: for the first login |
| A USB serial adapter | optional: for boot logs. See NVIDIA's Developer Kit User Guide for the debug UART pins |

## 3. Install and check

```bash
./build.sh deps            # lists what is missing
./build.sh deps --install  # sudo apt-get install -y …
```

The list is NVIDIA's own (`tools/l4t_flash_prerequisites.sh` in the driver package, R36.4.3) plus kernel
build tools:

| From NVIDIA's prerequisites script | For building |
| --- | --- |
| `abootimg binfmt-support binutils cpio cpp device-tree-compiler dosfstools iproute2 iputils-ping lbzip2 libxml2-utils netcat-openbsd nfs-kernel-server openssl python3-yaml qemu-user-static rsync sshpass udev uuid-runtime whois xmlstarlet zstd lz4` | `build-essential bc bison flex libssl-dev libncurses-dev libelf-dev kmod patch wget ca-certificates usbutils` |

`qemu-user-static` and `binfmt-support` matter: the root filesystem is an arm64 userland, and NVIDIA's
scripts run commands *inside* it (`apply_binaries.sh`, `l4t_update_initrd.sh`, `l4t_create_default_user.sh`)
through qemu emulation. Without them those steps fail with errors about `qemu-aarch64-static`.

Quick sanity checks:

```bash
uname -m                              # x86_64
. /etc/os-release; echo "$PRETTY_NAME"   # Ubuntu 22.04.x LTS
sysctl net.ipv6.conf.all.disable_ipv6    # 0
df -h .                                # free space where build/ will live
./build.sh --dry-run all | less -R       # reads the whole recipe, changes nothing
```

To put `build/` on another disk, set `BUILD_DIR=/mnt/big/jetson-build` in `config/local.conf`.
The path must not contain spaces or colons (NVIDIA's kernel build refuses them).

## 4. Where things end up

| Path | What |
| --- | --- |
| `build/downloads/` | the four archives (cached; deleted only by `distclean`) |
| `build/toolchain/` | NVIDIA's reference compiler |
| `build/work/Linux_for_Tegra/` | **the working tree**: driver package + rootfs + sources. NVIDIA's scripts run from here |
| `build/deploy/` | `FLASH.txt` and a link to the working tree |
| `build/logs/` | one log file per step, colours stripped |

Next: [03 · Boot firmware](03-bootloader-and-firmware.md) · Prev: [01 · Boot flow](01-boot-flow.md)
