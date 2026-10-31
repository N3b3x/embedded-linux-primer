# 09 · Troubleshooting

Organised by **the last thing you saw**. The first half is about the build, the second about the board.
Every build step writes a log to `build/logs/<step>.log` (a link to the newest one), and the error trap
prints the failing command, the script line and the log path.

> The board has not been booted on hardware by the authors of this repository (see the status table in the
> [README](../README.md)). The boot-time entries are what the sources say should happen and where to look;
> the build-time entries are things that really happened while this board was brought up.
> **For the first power-on, start with [14 · First-boot checklist](14-first-boot-checklist.md)**: it lists the
> log line each stage prints, and the decision order for a silent board. If the mainline stack misbehaves, the
> quickest experiment is `./build.sh -s st all` and the same card reader ([15](15-two-stacks.md)).

## Build time

### `fatal error: asm/arch/stm32.h: No such file or directory` (U-Boot)

U-Boot was built with `ARCH=arm64`. U-Boot calls the whole ARM family `ARCH=arm`; 64-bit is chosen by
`CONFIG_ARM64` in the defconfig. `scripts/firmware.sh` sets it for you (`MAKE_ARCH=arm`); you only see
this when you run `make` by hand with the kernel's habit of `ARCH=arm64`.

### `Device Tree Source (dts/upstream/src/arm64/stm32mp257f-dk.dtb) is not correctly specified`

`DEVICE_TREE` needs the vendor directory: `DEVICE_TREE=st/stm32mp257f-dk`. Newer U-Boot versions take their
board device trees from a copy of the Linux ones, laid out as `<vendor>/<board>`.

### `CFG_SCMI_SCPFW=y requires CFG_SCP_FIRMWARE configuration` (OP-TEE)

OP-TEE embeds Arm's SCP-firmware as its SCMI server and wants its source tree. The script clones it to
`build/src/scp-firmware` and passes `CFG_SCP_FIRMWARE`; if you call `make` yourself, pass it too. Also
install `cmake`.

### `One and only one DDR type must be defined` (TF-A)

TF-A compiles exactly one DDR driver. The DK has LPDDR4: `STM32MP_LPDDR4_TYPE=1`
(`TFA_DDR_TYPE_FLAG`). A different board may have DDR3 or DDR4.

### `fip.bin is larger than the 4096 KiB 'fip' partition`

The FIP grew (a bigger U-Boot, OP-TEE with more features). Raise `FIP_SIZE_KB` and make sure the end of the
`fip` partition stays below the `u-boot-env` partition at 9 MiB; `scripts/image.sh` checks both.

### `ModuleNotFoundError: No module named 'PIL'` (OP-TEE, `-s st`)

ST's OP-TEE 4.0 renders a font into its user-space libraries with a Python script that needs Pillow:
`sudo apt-get install python3-pil python3-cryptography` (or `./build.sh -s st deps --install`).

### U-Boot's host tools fail with SWIG or `pkg_resources` errors (`-s st`)

ST's U-Boot 2023.10 predates SWIG 4.3 and Python 3.13. Ubuntu 24.04 (SWIG 4.2, Python 3.12) builds it as is; on a newer
host take ST's two fixes, `0002-Fixup-SWIG-4.3-API-changed.patch` and
`0003-BINMAN-use-importlib.resources-instead-of-pkg_resour.patch`, from `recipes-bsp/u-boot/u-boot-stm32mp/` in
`github.com/STMicroelectronics/meta-st-stm32mp` (tag `wrynose_v26.02.18`), and put them in `patches/st/u-boot/`.

### `Sector 34 already used` from `sfdisk` (image, `-s st`)

The script puts `first-lba: 34` in the partition script for ST's layout. If you see this message, a hand-written script
or an edited `scripts/image.sh` lets `sfdisk` use its default first sector, 2048.

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

### `ERROR: BL2 is larger than the 256 KiB fsbla partition`

`FSBL_SIZE_KB` is too small for a build with more debug output. BL2 here is 175,080 bytes at log level 20;
log level 40 adds code and strings (ST's `DEBUG=1` build is 200,744 bytes).

### Every `curl`/`git` step fails

Check the proxy. Sources come from `review.trustedfirmware.org`, `github.com`, `git.gitlab.arm.com`,
`cdn.kernel.org`, `developer.arm.com`, `deb.debian.org` and `dl-cdn.alpinelinux.org`.

## Board time: nothing on the console

1. **Right port, right speed?** 115200 8N1. On Linux `dmesg | tail` after plugging the USB cable shows the
   name (usually `ttyACM0`). Close other programs that hold the port.
2. **Boot switches** set for the SD card ([07](07-flashing-and-booting.md#2-set-the-board-to-boot-from-the-sd-card)).
   With the wrong setting the ROM looks elsewhere and prints nothing.
3. **Card seated, written, intact?** Re-write it and look at the partition table on your PC:

   ```bash
   sudo sfdisk -d /dev/sdX                 # mainline: fsbla1, fsbla2, fip, u-boot-env, rootfs; -s st: eight (06)
   sudo dd if=/dev/sdX of=/tmp/bl2.bin bs=512 skip=2048 count=342 && cmp /tmp/bl2.bin <(cat build/deploy/tf-a-stm32mp257f-dk.stm32 /dev/zero | head -c $((342*512)))
   ```

   (`skip=34` instead of 2048 and `build/deploy-st/tf-a-stm32mp257f-dk-ca35tdcid-ostl.stm32` for `-s st`.)
   The names must be exactly `fsbla1`/`fsbla2` and `fip` (or `fip-a`/`fip-b`): the ROM and BL2 look for them by name.
4. Rebuild BL2 with more output (`TFA_LOG_LEVEL=40`, see [07](07-flashing-and-booting.md#4-power-on-and-what-to-look-for)).
5. **Boot the other stack.** If `./build.sh -s st all` (or the mainline one) prints BL2 on the same board, cable and card
   reader, the board is fine and this stack is the problem ([14](14-first-boot-checklist.md#2-if-the-first-boot-is-silent)).

## BL2 starts, then stops

| Last BL2 line | Likely cause |
| --- | --- |
| nothing after `Reset reason` | DDR training failed: wrong DDR type flag for the board, or the DDR firmware is not the one TF-A expects. Compare `TFA_DDR_TYPE_FLAG` with your board. |
| `Could NOT find the fip partition!` | the `fip` partition (type GUID `19d5df83-…`, or named `fip`) is missing: `plat/st/common/bl2_io_storage.c` |
| `Unable to find metadata partition "metadata1"` or `No partition with the uuid mentioned in metadata` (`-s st`) | the FWU metadata partitions are missing, or no partition has the PARTUUID of `fip-a`: the card was not written by `-s st` |
| a load or hash error for an image | the FIP is larger than its partition and was truncated when written, or the card is bad |

## U-Boot starts but Linux does not

You see the U-Boot banner and `Boot over mmc0!`, then either a prompt (`STM32MP>`) or a loop.

```text
STM32MP> mmc list                      # which numbers do the controllers have?
STM32MP> part list mmc 0               # five partitions (st: eight), the last marked bootable ("Bootable")
STM32MP> ls mmc 0:5 /boot              # Image, the DTBs, extlinux/   (st: mmc 0:8)
STM32MP> printenv boot_targets boot_instance
```

* No partition says bootable: the card was not written by `scripts/image.sh` (the `LegacyBIOSBootable`
  attribute is missing). U-Boot then looks at partition 1, `fsbla1`, which has no filesystem.
* It behaves as if it had other ideas about what to boot (a different `boot_targets`, an old `bootcmd`): **a stale
  U-Boot environment.** `./build.sh flash` erases `u-boot-env` for this reason; a card written another way still carries
  the old variables. `env default -a; saveenv` at the prompt resets them, or zero the partition from your PC
  ([06](06-sdcard-image.md)).
* `ls` shows nothing: the rootfs is not readable (wrong filesystem, truncated write).
* Boot by hand to separate "U-Boot cannot find it" from "Linux cannot start":

```text
STM32MP> setenv bootargs root=PARTUUID=6d70326b-0000-4000-8000-000000000001 rootwait rw earlycon console=ttySTM0,115200
STM32MP> load mmc 0:5 ${kernel_addr_r} /boot/Image
STM32MP> load mmc 0:5 ${fdt_addr_r} /boot/stm32mp257f-dk-primer.dtb
STM32MP> booti ${kernel_addr_r} - ${fdt_addr_r}
```

(With `-s st`: partition `0:8`, `/boot/stm32mp257f-dk-ca35tdcid-ostl.dtb`, and add `modprobe.blacklist=etnaviv`.)

## Linux never finds the root filesystem

The kernel prints `Waiting for root device PARTUUID=6d70326b-0000-4000-8000-000000000001...` and nothing
happens (with `rootwait` it waits forever by design; without it it panics with *"VFS: Unable to mount
root fs"*). The kernel cannot see the SD card. Two things can cause that on this board:

1. **The SD controller never probed because its power supply never appeared.** This is the one specific to
   this firmware stack, and the reason the default device tree is `stm32mp257f-dk-primer.dtb`.
   The upstream `stm32mp257f-dk.dts` says
   `&sdmmc1 { vmmc-supply = <&scmi_vdd_sdcard>; vqmmc-supply = <&scmi_vddio1>; }`, supplies that come from
   an **SCMI voltage domain** (protocol `0x17`, `scmi_regu` in `stm32mp251.dtsi`). OP-TEE 4.11.0's SCMI
   server for this SoC serves only the clock (`0x14`) and reset (`0x16`) protocols
   (`core/arch/arm/dts/stm32mp25-st-scmi-cfg.dtsi`, `core/lib/scmi-server/conf-optee-stm32mp2.mk`). With
   no regulator provider the SD controller's driver is deferred again and again. If you boot the stock DTB
   by mistake, boot with `deferred_probe_timeout=5` added to `KERNEL_CMDLINE_EXTRA`: the kernel then prints
   `deferred probe pending:` lines (`drivers/base/dd.c`) naming the missing supply. ST's own OP-TEE builds do
   serve that protocol; if you use them, boot the stock DTB. To compare on the board, choose the *other* entry in
   the boot menu (shown for three seconds before the kernel starts): the primer tree should reach `mmc0`, the
   stock one should hang on the SCMI supply with the mainline OP-TEE. With `-s st` the question does not arise.
   See [11](11-secure-world-and-scmi.md#what-this-repository-had-to-work-around).
2. **The root is named wrongly.** `root=PARTUUID=` must match the `uuid=` in the sfdisk script
   (`ROOTFS_PARTUUID` in the config). The kernel needs `CONFIG_EFI_PARTITION=y` built in and no
   initramfs; the script checks the options at configuration time.

> **Not confirmed on hardware.** The workaround replaces the supplies by fixed regulators on the
> assumption that the card is already powered (BL2 and U-Boot read it before Linux starts). If your board
> shows something else, this is the first place to look.

## Kernel panic with an ext4 "Unknown parameter" message

A vendor Yocto build for this very kit on a 6.6 kernel panicked with `ext4: Unknown parameter 'noatime'`
followed by `VFS: Unable to mount root fs`: the command line carried `rootflags=ro,noatime`, and the kernel
handed that string to ext4 as filesystem parameters, where `noatime` is not one. This repository avoids the
trap: **no `rootflags=`** anywhere; mount options live in `/etc/fstab` (`defaults,noatime`), which is read
after the root is mounted.

## A GPU driver takes the board down

The same vendor stack found that loading the `etnaviv` GPU driver switched on the GPU's PLL over SCMI and
crashed OP-TEE 4.0 (`clk_stm32_pll_init`). On the **mainline stack** it does not apply: the 6.18 device trees of
this board have no GPU node at all (`grep -rn vivante arch/arm64/boot/dts/st/` finds nothing), so `etnaviv` has
nothing to bind to, and `config/kernel/00-base.cfg` now also switches it off (`# CONFIG_DRM_ETNAVIV is not set`).
On the **ST stack** it does apply: ST's device tree enables the GPU node, ST's OP-TEE 4.0 is the one that
panics, and the kernel is built without `etnaviv` *and* started with `modprobe.blacklist=etnaviv`. If the secure
world misbehaves right after boot, `lsmod | grep etnaviv` is the first check.

## No network

The DK's Ethernet is `ethernet1` in the device tree (RGMII, a Realtek PHY; the driver is the module
`dwmac-stm32`, PHY driver built in). On Debian the interface appears as `end0` and `systemd-networkd`
asks for DHCP on it. `ip -br link`, `dmesg | grep -i -E 'stmmac|dwmac|realtek'` and `lsmod | grep stmmac`
tell you whether the driver loaded; on Alpine the `coldplug` script loads modules.

## Slow or wrong time

There is no battery-backed clock configured in this first-steps image; `systemd-timesyncd` sets the time
over the network. Without a network it starts in 1970.

Next: [10 · Versions](10-versions.md).
