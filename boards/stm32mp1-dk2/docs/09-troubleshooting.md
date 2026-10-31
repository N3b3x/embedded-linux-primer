# 09 · Troubleshooting

Organised by **the last thing you saw**. The first half is about the build, the second about the board.
Every build step writes a log to `build/logs/<step>.log` (a link to the newest one), and the error trap
prints the failing command, the script line and the log path. For a first run on hardware, use the
checklist in [15](15-first-boot-checklist.md) first: it tells you what each stage prints when it works.

> The board has not been booted on hardware by the authors of this repository (see the status table in the
> [README](../README.md)). The boot-time entries are what the sources say should happen and where to look;
> the build-time entries are things that really happened while this board was brought up.

## Build time

### `E: install arch-test for foreign architecture support` (Debian root filesystem)

`mmdebstrap` builds an `armhf` system on a PC of another architecture and wants the `arch-test` package to
check that it can run it. `./build.sh deps --install` installs it; by hand: `sudo apt install arch-test`.
(This happened while bringing this board up, in a container on an ARM64 PC.)

### `armhf binfmt handler missing: sudo apt install qemu-user-static binfmt-support`

The packages of the Debian root filesystem are 32-bit ARM and their install scripts must *run* during the
build. A PC that cannot execute 32-bit ARM code needs `qemu-user-static` and a registered `binfmt_misc`
handler (named `qemu-arm`; Docker Desktop names it `arm`, and the script accepts both). Check with
`ls /proc/sys/fs/binfmt_misc/`. In Docker the handler lives in the VM: `--privileged` is not needed for it,
only for rootless mmdebstrap.

### `fatal error: asm/arch/stm32.h: No such file or directory` (U-Boot)

U-Boot was built with `ARCH=arm64`, or with the wrong compiler. This 32-bit chip wants `ARCH=arm` and
`arm-none-linux-gnueabihf-`; `scripts/firmware.sh` sets them for you. You only see this when you run `make` by
hand.

### `Device Tree Source (dts/upstream/src/arm/stm32mp157c-dk2-scmi.dtb) is not correctly specified`

`DEVICE_TREE` needs the vendor directory: `DEVICE_TREE=st/stm32mp157c-dk2-scmi`. Newer U-Boot versions take
their board device trees from a copy of the Linux ones, laid out as `<vendor>/<board>`.

### TF-A: the build runs out of SYSRAM

TF-A allows **one** boot medium per build (`STM32MP_SDMMC=1`); selecting a second (`STM32MP_EMMC`,
`STM32MP_UART_PROGRAMMER`, …) "won't build or boot" (`docs/plat/st/stm32mpus.rst`) because BL2 must fit in
88 KB of SYSRAM.

### `fip.bin is larger than the 4096 KiB 'fip' partition`

The FIP grew (a bigger U-Boot, OP-TEE with more features). Raise `FIP_SIZE_KB` and make sure the end of the
`fip` partition stays below the `u-boot-env` partition at 9 MiB; `scripts/image.sh` checks both.

### `ERROR: unknown option: -j6`

Options that take a value are separate words: `./build.sh -j 6 kernel`.

### The kernel build fails with odd "No such file" errors on macOS

The kernel tree has files that differ only in letter case. Build on a Linux file system: a Docker volume,
or a Linux VM disk ([02](02-host-setup.md#using-a-container-on-macos-or-windows)).

### Debian rootfs: `cannot open …/debian-passwords: Permission denied`

`mmdebstrap --mode=unshare` runs its hook in a nested user namespace in which your files belong to "someone
else". The script writes the hash file world-readable for that reason, but a file left by an earlier failed
run keeps its old mode: delete `build/work/debian-passwords` and run `./build.sh rootfs` again.

### Debian rootfs fails to start the namespace on Ubuntu 24.04

`sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`, or just let the script fall back to `sudo`,
or use `./build.sh -r alpine rootfs`.

### `ERROR: BL2 is larger than the 256 KiB fsbl partition`

`FSBL_SIZE_KB` is too small for a build with more debug output. BL2 here is 209,316 bytes at log level 20;
log level 40 adds code and strings.

### Every `curl`/`git` step fails

Check the proxy. Sources come from `review.trustedfirmware.org`, `github.com`, `cdn.kernel.org`,
`developer.arm.com`, `deb.debian.org` and `dl-cdn.alpinelinux.org`.

## Board time: nothing on the console

1. **Right port, right speed?** 115200 8N1. On Linux `dmesg | tail` after plugging the USB cable shows the
   name (usually `ttyACM0`). Close other programs that hold the port.
2. **Boot switches** set for the SD card ([07](07-flashing-and-booting.md#2-set-the-board-to-boot-from-the-sd-card)).
   With the wrong setting the ROM looks elsewhere and prints nothing.
3. **Card seated, written, intact?** Re-write it and look at the partition table on your PC:

   ```bash
   sudo sfdisk -d /dev/sdX                 # five partitions: fsbl1, fsbl2, fip, u-boot-env, rootfs
   ```

   The names must be exactly `fsbl1`/`fsbl2`/`fip`: the ROM looks for them by name.
4. Rebuild BL2 with more output (`TFA_LOG_LEVEL=40`, see [07](07-flashing-and-booting.md#4-power-on-and-what-to-look-for)).

## BL2 starts, then stops

| Last BL2 line | Likely cause |
| --- | --- |
| `Secure chip: TRUSTED_BOARD_BOOT must be enabled` | the chip is *closed* (secure-boot fuses burnt): it only runs signed code. Not a kit state ST ships |
| `Invalid DDR init: error …` | the DDR3 controller setup failed: the DDR description of the DTB does not match the board's memory |
| `PMIC voltages init failed` | BL2 could not talk to the STPMIC1 on I²C4 |
| `SDMMC1 init failed` | BL2 cannot read the card: bad card, bad seating, or a corrupt card |
| `Could NOT find the fip partition!` | the `fip` partition (type GUID `19d5df83-…`, or named `fip`) is missing: `plat/st/common/bl2_io_storage.c` |
| `BL2: Failed to load image id …` | a file named in the FIP's `fw-config` is missing, or the FIP was truncated when written |
| `OPTEE header parse error.` | `tee-header_v2.bin` is not an OP-TEE v2 header: the FIP holds the wrong BL32 file |

## OP-TEE starts, U-Boot does not

BL2 printed `BL2: Booting BL32` and OP-TEE printed some `I/TC:` lines.

* No line at all from OP-TEE after `Booting BL32`: the image was loaded to the wrong place or the secure RAM
  does not match the memory size. The board has 512 MB: the OP-TEE tree must be in OP-TEE's 512 MB list
  (`stm32mp157c-dk2-scmi.dts` is), which puts it at `0xde000000`.
* OP-TEE prints `Primary CPU switching to normal world boot` and then nothing: U-Boot is not running. Check
  that the U-Boot in the FIP is the one you built (`fiptool info`); then build U-Boot with the early debug
  console, or compare `DEVICE_TREE` with [03](03-firmware-and-uboot.md#step-2-u-boot): the F-DK2 tree
  without the board's `-u-boot.dtsi` leaves the UART unconfigured before relocation.

## U-Boot starts but Linux does not

You see the U-Boot banner and `Boot over mmc0!`, then either a prompt (`STM32MP>`) or a loop.

```text
STM32MP> mmc list                      # which numbers do the controllers have?
STM32MP> part list mmc 0               # five partitions, the last marked bootable ("Bootable")
STM32MP> ls mmc 0:5 /boot              # zImage, the DTB, extlinux/
STM32MP> printenv boot_targets boot_device boot_instance
```

* No partition says bootable: the card was not written by `scripts/image.sh` (the `LegacyBIOSBootable`
  attribute is missing). U-Boot then looks at partition 1, `fsbl1`, which has no filesystem.
* `ls` shows nothing: the rootfs is not readable (wrong filesystem, truncated write).
* Boot by hand to separate "U-Boot cannot find it" from "Linux cannot start":

```text
STM32MP> setenv bootargs root=PARTUUID=6d703135-0000-4000-8000-000000000001 console=ttySTM0,115200 rootwait rw earlycon
STM32MP> load mmc 0:5 ${kernel_addr_r} /boot/zImage
STM32MP> load mmc 0:5 ${fdt_addr_r} /boot/stm32mp157f-dk2.dtb
STM32MP> bootz ${kernel_addr_r} - ${fdt_addr_r}
```

## Linux prints nothing after `Starting kernel ...`

Add `earlycon` (it is there by default) and check that the device tree is the DK2's. A kernel built from
`stm32_defconfig` (the Cortex-M configuration) or with the 64-bit board's `Image` does not start at all.

## Linux never finds the root filesystem

The kernel prints `Waiting for root device PARTUUID=6d703135-0000-4000-8000-000000000001...` and nothing
happens (with `rootwait` it waits forever by design; without it it panics with *"VFS: Unable to mount root
fs"*). The kernel cannot see the SD card. Two things can cause that on this board:

1. **The SD controller never probed because a dependency never appeared.** On this board the card's supply
   is an SCMI regulator (`vmmc-supply = <&scmi_v3v3>`) and the roots of its clock tree (HSE, the PLLs) belong to OP-TEE. If the OP-TEE in the
   FIP does not answer SCMI (the OP-TEE tree is wrong, or OP-TEE crashed), the `mmci` driver is deferred again
   and again. Boot with `deferred_probe_timeout=5` added to `KERNEL_CMDLINE_EXTRA`: the kernel then prints
   `deferred probe pending:` lines (`drivers/base/dd.c`) naming what is missing. Look earlier in the log for
   `optee:` and `scmi` lines ([11](11-secure-world-and-scmi.md)); if there are none, the driver never reached
   OP-TEE.
2. **The root is named wrongly.** `root=PARTUUID=` must match the `uuid=` in the sfdisk script
   (`ROOTFS_PARTUUID` in the config). The kernel needs `CONFIG_EFI_PARTITION=y` built in and no
   initramfs; the script checks the options at configuration time.

## Kernel panic with an ext4 "Unknown parameter" message

A vendor Yocto build for a sibling kit on a 6.6 kernel panicked with `ext4: Unknown parameter 'noatime'`
followed by `VFS: Unable to mount root fs`: the command line carried `rootflags=ro,noatime`, and the kernel
handed that string to ext4 as filesystem parameters, where `noatime` is not one. This repository avoids the
trap: **no `rootflags=`** anywhere; mount options live in `/etc/fstab` (`defaults,noatime`), which is read
after the root is mounted.

## No network

The DK2's Ethernet is `ethernet0` in the device tree (RGMII; the driver `dwmac-stm32` is built in). On Debian
the interface appears as `end0` and `systemd-networkd` asks for DHCP on it. `ip -br link`,
`dmesg | grep -i -E 'stmmac|dwmac'` tell you whether the driver loaded. The MAC address comes from the chip's
OTP (`doc/board/st/stm32mp1.rst`, "MAC Address").

## No display, no Wi-Fi

Both are modules (`DRM_STM`, `DRM_PANEL_ORISETECH_OTM8009A`, `BRCMFMAC`). On Debian `udev` loads the display
modules a while after the console is up; Wi-Fi also needs the Broadcom firmware file in
`/lib/firmware/brcm/`, which this repository does not download. Neither is needed to log in.

## Slow or wrong time

There is no battery-backed clock configured in this first-steps image; `systemd-timesyncd` sets the time
over the network. Without a network it starts in 1970.

Next: [10 · Versions](10-versions.md).
