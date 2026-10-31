# 09 · Troubleshooting

[Docs](README.md) › **09 · Troubleshooting**

Every step writes a full log to `build/logs/<step>-<timestamp>.log` (and
`build/logs/<step>.log` → the latest). On failure the scripts print the failing
command, the line and the log path. Re-run with `-v` to see full compiler
command lines.

## Build problems

| Symptom | Cause / fix |
| --- | --- |
| `missing host tool(s): ...` | `./build.sh deps --install` |
| `cert-to-efi-sig-list: not found` / `capsule_esl_file Error 127` | U-Boot's capsule authentication needs **efitools**: `sudo apt install efitools` |
| `EULA not accepted` | add `--accept-eula`, or `ACCEPT_FSL_EULA=1` in `config/local.conf` |
| `sha256sum: WARNING: 1 computed checksum did NOT match` | corrupt/partial download: delete the file in `build/downloads/` and retry. If it keeps failing, the upstream file changed: double-check the URL/version |
| `fatal: couldn't find remote ref <sha>` | the pinned `*_REV` is not on that branch (typo, or upstream force-pushed). Set `*_REV=` (empty) to use the branch tip |
| `... has local modifications; commit/stash them ...` | `--update` protects your edits in `build/src/*`. Turn them into patches ([08-customizing.md](08-customizing.md)) or `git -C build/src/<x> stash` |
| TF-A: `array subscript 0 is outside array bounds`, or `LOAD segment with RWX permissions` | already handled with `E=0`. If a newer GCC adds new errors, try `TOOLCHAIN=system` or an older `ARM_TOOLCHAIN_VERSION` |
| imx-mkimage: `No rule to make target 'imx8mp-var-...dtb'` | a name in `UBOOT_DTBS` does not exist in this U-Boot (renamed between releases): `ls build/src/uboot-imx/arch/arm/dts/imx8mp-var*` |
| imx-mkimage prints `ERROR: pad_image.sh: Could not find file tee.bin` | **harmless**: OP-TEE (a secure-world OS) is optional and not built here; the image is created without it |
| imx-mkimage: `lpddr4_pmu_train_..._202006.bin: No such file` | firmware not unpacked: `./build.sh uboot firmware` |
| kernel: `merge_config.sh: ... not set` warnings | a fragment option depends on something not enabled; the warning names it |
| `mmdebstrap: ... binfmt` / `exec format error` | `sudo apt install qemu-user-static binfmt-support`, then check `ls /proc/sys/fs/binfmt_misc/qemu-aarch64` |
| `mmdebstrap` asks for a sudo password | expected without `uidmap`. Install `uidmap` for rootless mode, or use `-r alpine` |
| Out of disk space | the kernel needs ~7 GB. `./build.sh clean` frees objects, `ccache -C` the cache |

## Boot problems (watch the serial console!)

| What you see | Likely cause |
| --- | --- |
| **Nothing at all** on the console | wrong serial port/baud (115200 8N1). Boot switch not on SD. Card not flashed (check `xxd -s 32K -l 16 /dev/sdX` shows `d1 00 20 41`). You wrote to a partition (`/dev/sdX1`) instead of the disk |
| `U-Boot SPL` then hangs / DDR errors | wrong or missing DDR firmware, or an image built for another board |
| U-Boot prompt `u-boot=>` instead of autoboot | `bootcmd` failed. Run `run bsp_bootcmd` to see the error, and `printenv` |
| `** File not found /boot/Image.gz **` | kernel not in partition 1 `/boot`. The old scripts' FAT `BOOT` partition layout does not work with this U-Boot |
| `fdt_file=... ** File not found` | DTB with that name is missing: `ls /boot/*.dtb` on the card. Set `fdt_file` in `/boot/uEnv.txt` |
| `Starting kernel ...` and then silence | wrong console. DART = `ttymxc0`, SOM/SMARC = `ttymxc1`. Or a DTB that doesn't match the hardware |
| `VFS: Unable to mount root fs` | `root=` points at the wrong device. Check `printenv mmcargs mmcblk`. SD = `mmcblk1`, eMMC = `mmcblk2` |
| `Kernel panic - not syncing: No working init found` | the rootfs tarball is incomplete, or `/lib` was replaced by a directory (`--keep-directory-symlink` prevents this in `image.sh`) |
| Kernel ends with `Run /sbin/init as init process` (+ a few `deferred probe pending` lines) and no login | userspace is running but the login is on another UART. Images built before the console auto-detect put Alpine's getty on `ttymxc0` only, while VAR-SOM/SMARC use `ttymxc1`. Rebuild with `./build.sh -r alpine rootfs && ./build.sh image` |
| `lsmod` empty; no `/dev/rtc0`; `No soundcards found`; SPI `can't get the TX DMA channel` | (Alpine images built before the coldplug fix) no kernel modules are loaded. Run `/sbin/coldplug` if present, or rebuild with `./build.sh -r alpine rootfs && ./build.sh image` |
| `date` shows 1970 or 2000 | the RTC was never set: `date -u -s "YYYY-MM-DD hh:mm:ss" && hwclock -u -w` |
| non-root programs fail with `/dev/null: Permission denied` | (old Alpine images) `mdev -s` without `/etc/mdev.conf` made it root-only. Fixed in current images |
| `eth0: cannot attach to PHY (error: -ENODEV)` | no PHY populated for that port on your module: use `eth1` ([12](12-board-tour.md#6-network)) |
| `pca953x 3-0021: failed writing register: -6`, TPM/PCIe deferred | Symphony carrier without the PCAL6408 expander at 0x21 ([12](12-board-tour.md#11-whats-not-working-on-this-board-and-why)) |
| login prompt never appears (Debian) | `serial-getty@ttymxc0` didn't start: boot with `kernelargs=systemd.log_level=debug` in uEnv.txt |
| `modprobe: FATAL: Module ... not found in directory /lib/modules/<ver>` | modules from a different kernel build. Rebuild with the same `KERNEL_LOCALVERSION` and re-flash with `--kernel-only` |
| No network on Debian | interfaces are named `end0`/`end1`. Check `networkctl` and `journalctl -u systemd-networkd` |

## First boot on a DART checklist

Only the VAR-SOM-MX8M-PLUS on Symphony has been booted on hardware. A DART-MX8M-PLUS on Sonata
has been **built, never run**, so look at how U-Boot recognised the module before you trust anything else.
(Everything here is read from Variscite's U-Boot, `board/variscite/imx8mp_var_dart/`, at the pinned commit.)

How U-Boot decides: the SPL reads two strap pins (`GPIO2_IO11` high = VAR-SOM, `GPIO2_IO07` high =
SMARC, otherwise DART). U-Boot then reads the SoM EEPROM (`Part number`, `SOM revision`) and the
carrier EEPROM (`carrier_name`) and `findfdt` builds the DTB name from `board_name`, `som_rev`,
`som_has_wbe` and `carrier_name`. Two traps:

* A DART whose SoM EEPROM is not programmed reads `som_rev` 0, so `findfdt` picks the `-1.x` device tree.
* If the module is not recognised at all, `board_name` stays unset and `findfdt` falls into its `else`
  branch and chooses **`imx8mp-var-smarc-echo.dtb`**, the wrong module.

The console is `ttymxc0` on a DART (the USB-UART connector of the Sonata carrier) and `ttymxc1` on a VAR-SOM and SMARC.

**What to look at in the serial log** (from power-on; stop autoboot with a key):

| Line | Means |
| --- | --- |
| `Part number: VSM-DT8MP-…` (VSM-MX8MP-… = VAR-SOM, VSM-SC8MP-… = SMARC) | which module the EEPROM says it is |
| `SOM revision: x.y` | below 2.0 gives the `-1.x` DTB |
| `Model: …` | the U-Boot device tree it picked |
| `fdt_file=…` (printed by `loadfdt` right before the kernel is loaded) | the Linux DTB it will load |
| `Kernel command line: console=…` | `ttymxc0` expected on DART |

**In U-Boot** (type a key at `Hit any key to stop autoboot`):

```text
printenv board_name som_rev carrier_name som_has_wbe fdt_file console
run findfdt; printenv fdt_file          # what the automatic choice gives
setenv fdt_file imx8mp-var-dart-sonata.dtb; boot      # one boot only, not saved
```

`ls mmc 1:1 /boot` lists the DTBs on the card. Use `-1.x-sonata`, no suffix or `-wbe-sonata` as the module requires.
Do not `saveenv` while experimenting: a saved `fdt_file` survives later flashes of `uuu emmc --rootfs-only`.

**What to capture and send:** the full raw serial log (`picocom -b 115200 --logfile boot.log /dev/ttyUSB0`,
started before power-on), `./build.sh info`, and `sfdisk -d /dev/sdX` of the card (or `sfdisk -d /dev/mmcblk2` on the board).

## Useful U-Boot commands

```text
printenv                        show everything
printenv fdt_file board_name som_rev carrier_name
run findfdt; printenv fdt_file  which DTB it would pick
mmc list; mmc dev 1; mmc part   storage overview
ls mmc 1:1 /boot                list the boot files
setenv kernelargs loglevel=8    more kernel output (lost on reset unless saveenv)
env default -a; saveenv         back to factory environment
```

## Getting help

* Variscite DART-MX8M-PLUS wiki: <https://variwiki.com/index.php?title=DART-MX8M-PLUS>
* NXP i.MX Linux release notes / user guide for the LF release you build
* Upstream sources: <https://github.com/varigit>

---

← [08 · Customizing](08-customizing.md) · [Index](README.md) · [10 · Versions](10-versions.md) →
