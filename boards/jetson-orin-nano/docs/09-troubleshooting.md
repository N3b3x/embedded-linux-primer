# 09 · Troubleshooting

[Docs](README.md) › **09 · Troubleshooting**

Symptom first. The quoted messages are the ones the scripts and NVIDIA's tools (R36.4.3) print. Every step writes a
log to `build/logs/<step>-<time>.log`; the flash tool also writes `build/work/Linux_for_Tegra/initrdlog/`.

## Before the build

| Symptom | Cause and fix |
| --- | --- |
| `NVIDIA's Jetson Linux tools run only on an x86-64 Linux PC` | This computer is a Mac, Windows or ARM64 machine. Use an Ubuntu 22.04 x86-64 PC or VM. `--dry-run` still works anywhere |
| `Missing packages: …` after `deps` | `./build.sh deps --install` |
| `tar: …: Directory renamed before its status could be extracted` while unpacking `kernel_src.tbz2` | `build/` is on a **case-insensitive** filesystem (macOS/Windows folder, Docker bind mount of one). The Linux source tree has file names that differ only in case. Move `BUILD_DIR` to a Linux filesystem |
| `source directory cannot contain spaces or colons` | NVIDIA's Makefile rejects such paths. Set `BUILD_DIR` to a plain path |
| `sha256sum: WARNING: 1 computed checksum did NOT match` | Corrupt or changed download. Delete the file in `build/downloads/` and re-run. If NVIDIA re-published the file, see [10 · Versions](10-versions.md) |
| Download stops, `wget` error | Re-run: `fetch` resumes (`--continue`) |

## The root filesystem step

| Symptom | Cause and fix |
| --- | --- |
| `Creating the default user accepts NVIDIA's Tegra Software License Agreement` | Read `Linux_for_Tegra/Tegra_Software_License_Agreement-Tegra-Linux.txt`, then run with `--accept-license` |
| `This script requires root privilege` (from `apply_binaries.sh`) | Run via `./build.sh rootfs`, which uses `sudo` |
| `The root filesystem, provided with this package, has to be extracted to this directory … with 'sudo'` | The sample rootfs was unpacked as a normal user. `./build.sh clean`, then run `rootfs` again |
| `ERROR: please install qemu-user-static package` | `./build.sh deps --install` (qemu and binfmt are in the list) |
| `Cannot find the Tegra software license agreement` | `apply_binaries.sh` did not complete: look in `build/logs/rootfs-*.log` for the first error |
| errors about `chroot`, `exec format error` | The qemu binfmt handler is not registered: `sudo systemctl restart binfmt-support` or `sudo update-binfmts --enable qemu-aarch64` |

## The kernel step

| Symptom | Cause and fix |
| --- | --- |
| `…gcc: No such file` or `cannot execute binary file` | The toolchain is x86-64 only; check `uname -m` |
| `make: *** … Illegal instruction` while compiling | You are running the x86-64 toolchain under CPU emulation (Docker or a VM on Apple Silicon). Emulators can crash on instructions the compiler uses. Build on a real x86-64 machine |
| `kernel headers/output directory … does not exist!` | NVIDIA's top-level Makefile did not find `KERNEL_HEADERS`. The scripts set it; if you run `make` by hand, point it at `source/kernel/kernel-jammy-src` |
| A patch fails: `Hunk #1 FAILED` | The patch does not match R36.4.3 sources. Regenerate it against the tree in `build/work/Linux_for_Tegra/source/` |
| New config option did not take effect | `grep CONFIG_FOO build/work/Linux_for_Tegra/source/kernel/kernel-jammy-src/.config`. A symbol with unmet dependencies is dropped by `olddefconfig`; enable the dependencies in the fragment |
| Modules do not load on the board (`Unknown symbol`, `invalid module format`) | `uname -r` and `ls /lib/modules` disagree: the Image and the modules come from different builds. Re-run `./build.sh kernel install` (it installs both) and flash again |

## Recovery mode and the USB link

| Symptom | Cause and fix |
| --- | --- |
| `lsusb -d 0955:` prints nothing | Not in recovery mode. Power off; jumper **REC–GND** on the 12-pin button header; USB-C to the PC (try another port and another cable); power on |
| A device `0955:` with a different number than expected | `7523` / `7623` Orin Nano, `7323` / `7423` Orin NX, `7023` / `7223` AGX Orin. Wrong module for these defaults |
| `No devices to flash` | The tool found no recovery device, or `udev` hid it. Replug, check `lsusb` |
| `Error, too many devices in RCM mode` / `Too many devices in RCM mode` | More than one Jetson in recovery mode on this PC. Unplug the others |
| `ERROR sshpass not found!` · `abootimg not found!` · `zstd not found!` | `./build.sh deps --install` |
| `IPv6 is disabled. Please enable ipv6 to use this tool` | `sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0` (and for the new `usb0` interface) |
| `Waiting for target to boot-up...` then `Timeout` and `Device failed to boot to the initrd flash kernel` | The recovery initrd did not start. Use a better cable or another port; try again from a fresh power cycle; capture the serial log if you can |
| `Device should have booted into initrd now. However, the host cannot connect to its ssh server` | The USB Ethernet link came up but SSH over IPv6 is blocked. Check firewall/VPN, `ping6 fe80::1%<interface>`. The message `Command failed: ping6 -c 1 fe80::1%…` says the same |
| `Network interface disappears after discovery` | Something took the USB interface away: a VM's USB passthrough, or a network manager that ignores NVIDIA's `NM_UNMANAGED` rule. Use a physical machine, or stop other tools managing `usb0`, and retry |
| NFS errors on the board | The PC's firewall blocks NFS on the USB link, or `nfs-kernel-server` is missing |
| Flash fails and says your `APPSIZE might be too small` | The root filesystem is larger than `APP_SIZE`. Raise it |
| After a failed run the PC still has NFS entries | The tool removes them on exit; if it was killed, delete the lines after `# Entry added by NVIDIA initrd flash tool` in `/etc/exports` and `sudo exportfs -ra` |

If a flash dies half way, the BootROM (which lives in the chip) normally lets you recover: put the module in recovery mode again and flash again.

## After flashing

| Symptom | Cause and fix |
| --- | --- |
| The board enters recovery mode on every power-up | The REC–GND jumper is still on |
| It boots the old OS from the SD card | UEFI's default order tries removable devices first. Flash with `-d` matching your intent (the boot-order overlay is then set), or choose in UEFI (**ESC** → Boot Manager) |
| No picture | Wait a minute; check DisplayPort; use SSH or the serial console; check UEFI's *Boot Manager* lists your drive |
| Stuck in UEFI shell | UEFI found no bootable device. Check the drive is installed and that the flash reported `Success`. `fs0:` and `ls EFI\BOOT` should show `BOOTAA64.efi` |
| Login rejected | The account is the one from `config/jetson-orin-nano.conf` (`jetson` / `jetson` by default) or your `local.conf` |
| `df -h /` shows 55 GB on a larger drive | The default `APP` size is 55 GiB. Set `APP_SIZE` and re-flash, or resize afterwards |

## Asking for help

Collect: `./build.sh info`, the log of the failing step, `lsusb`, `uname -a`, and the first error line. Include which of the status-table
items in the [README](../README.md) you have already passed.

Next: [10 · Versions](10-versions.md) · Prev: [08 · Customizing](08-customizing.md)
