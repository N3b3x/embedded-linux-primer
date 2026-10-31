# 05 · The root filesystem

[Docs](README.md) › **05 · Root filesystem**

On the SD-card boards the rootfs is a tarball you choose. Here it is a three-part assembly, and
`./build.sh rootfs` performs NVIDIA's documented recipe, as root.

## 1. The three parts

| # | What | Where it comes from | Command |
| --- | --- | --- | --- |
| 1 | **Sample root filesystem**: a bare Ubuntu 22.04 (jammy) arm64 userland, 1.8 GB compressed | `Tegra_Linux_Sample-Root-Filesystem_r36.4.3_aarch64.tbz2` | `sudo tar -xpf … -C Linux_for_Tegra/rootfs/` |
| 2 | **NVIDIA's userspace** on top: L4T core, GPU/display/camera/multimedia libraries, `nvpmodel`, `jetson_clocks`, `tegrastats`, the bootloader updater, the stock kernel modules and firmware, `extlinux.conf` and the initrd | the driver package: `nv_tegra/l4t_deb_packages/*.deb`, `nv_tegra/*.tbz2`, `kernel/*.tbz2` | `sudo ./apply_binaries.sh` |
| 3 | **A login account** (and hostname), so that first boot does not start NVIDIA's setup wizard | `tools/l4t_create_default_user.sh` | `sudo ./tools/l4t_create_default_user.sh -u … -p … -n … --accept-license` |

Run it:

```bash
./build.sh --accept-license rootfs        # idempotent: finished sub-steps are skipped
```

Why each part needs root: the sample filesystem contains files owned by root, device nodes and setuid
programs, which `tar -p` only recreates for root. `apply_binaries.sh` and `l4t_create_default_user.sh` run commands inside the
arm64 root filesystem through `qemu-user-static` and refuse to run without root (`This script requires root privilege`).

## 2. What `apply_binaries.sh` really does

From the script (R36.4.3):

1. installs `bootloader/extlinux.conf` as `rootfs/boot/extlinux/extlinux.conf`;
2. extracts NVIDIA's Debian packages (`nvidia-l4t-core`, `-cuda`, `-multimedia`, `-camera`, `-nvpmodel`, `-tools`,
   `-bootloader`, `-init`, `-initrd`, `-oem-config` and about forty more) into the rootfs, using the `nv-apply-debs.sh` helper in a qemu chroot;
3. unpacks `nvidia_drivers.tbz2`, `nv_tools.tbz2`, `nv_optee.tbz2`, `weston.tbz2`, `config.tbz2`, `graphics_demos.tbz2`;
4. unpacks the stock kernel modules and firmware (`kernel_supplements.tbz2`, `kernel_oot_modules.tbz2`,
   `kernel_display_supplements.tbz2`) and the kernel headers into `/usr/src`;
5. runs `tools/l4t_update_initrd.sh`, producing `rootfs/boot/initrd`, and copies it to `bootloader/l4t_initrd.img`.

So after this step you already have a complete, bootable system with **NVIDIA's stock kernel**. That is what
`--stock-kernel` uses. `./build.sh kernel` then replaces the kernel and modules.

## 3. The login account

`TARGET_USER`, `TARGET_PASSWORD` and `TARGET_HOSTNAME` (default `jetson` / `jetson` / `orin-nano`) go into
`l4t_create_default_user.sh`. **These are bench defaults.** Change them in `config/local.conf` before you connect the
board to a network anyone else can reach:

```bash
# config/local.conf
TARGET_USER=dev
TARGET_PASSWORD='a-better-password'
TARGET_HOSTNAME=orin-lab-1
```

The script's other options: `-a` enables autologin on the console (not wired in here); without `-p` it generates a random password
and prints it (`Creating: Username - …, Password - …`).

**Without an account** the first boot starts NVIDIA's *oem-config*: a wizard for license, language, user and network. NVIDIA's
*Flashing Support* chapter describes two ways to talk to it: on a monitor, or **headless over the same USB port you flashed with**
(the device appears on the Jetson as `ttyGS0` and on your PC as a serial port such as `/dev/ttyACM0`). Alternatively a UART on the
40-pin header (`ttyTHS0`), selected by `nv-oem-config-uart-port` in `<rootfs>/etc/nv-oem-config.conf` *before* flashing.
This repository skips the wizard; to keep it, delete the `l4t_create_default_user.sh` step from `scripts/rootfs.sh`.

## 4. Changing the root filesystem before flashing

The rootfs is an ordinary directory tree, `build/work/Linux_for_Tegra/rootfs/`, owned by root. Anything you
change there is written to the `APP` partition the next time you run `./build.sh image` (or `flash --full`):

```bash
# copy a file in
sudo install -m 0644 my.service build/work/Linux_for_Tegra/rootfs/etc/systemd/system/

# install a package inside the arm64 tree (needs qemu-user-static, which `deps` installed)
cd build/work/Linux_for_Tegra
sudo cp /usr/bin/qemu-aarch64-static rootfs/usr/bin/
sudo cp /etc/resolv.conf rootfs/etc/resolv.conf       # NVIDIA's own scripts save and restore this file; do the same if it matters
sudo chroot rootfs apt-get install -y htop
sudo rm rootfs/usr/bin/qemu-aarch64-static
```

> The `chroot` trick is the same mechanism NVIDIA's scripts use (`l4t_update_initrd.sh` copies `qemu-aarch64-static` in, runs
> `nv-update-initrd`, then removes it). Keep your changes small and scripted. Once your list grows, a product is better served
> by its own package or by a configuration-management step after first boot.

## 5. Size

`ROOTFSSIZE=55GiB` in `p3767.conf.common` is the default size of the `APP` partition, which is why NVIDIA asks for 64 GB or larger SD cards and USB
drives on this module. To change it, set `APP_SIZE=100GiB` (passed as `-S`; it must fit the device). NVIDIA's initrd-flash
README notes that the tool does not discover the device size: the XML's `num_sectors` has to describe the drive,
and the default layout assumes **64 GiB and above** for the external device.

## 6. Other root filesystems

NVIDIA's `Root File System` chapter describes building your own Ubuntu or Debian arm64 rootfs and using it in place of
the sample. The only requirements this repository adds: unpack it into `build/work/Linux_for_Tegra/rootfs/` as root *before* you run
`apply_binaries.sh` (delete `build/work/.stamp-rootfs-tar` and `.stamp-apply-binaries` first, so the steps re-run), and expect to
adjust `apply_binaries.sh`'s Debian package step if your distribution is not Ubuntu 22.04.
This is advanced and not verified here.

Next: [06 · Flash package](06-flash-package.md) · Prev: [04 · Kernel](04-kernel.md)
