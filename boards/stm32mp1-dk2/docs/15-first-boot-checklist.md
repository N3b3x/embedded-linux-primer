# 15 · First boot checklist: what to look for, and what to capture

This chapter is for the first time you put a card made by this repository into a real STM32MP157F-DK2. Nobody
has booted this build on the kit yet ([README](../README.md#what-has-been-checked)), so the most useful thing
you can do is to **record the boot** and compare it with what each stage should print. Every line quoted
below was read from the pinned sources (or, for the U-Boot and kernel lines, from the strings of the built
binaries); the file that prints it is named so you can check.

## 1. Before you power on

| Item | Setting |
| --- | --- |
| Serial settings | **115200 baud, 8 data bits, no parity, 1 stop bit (8N1), no flow control** (hardware and software off). The console is UART4 through the on-board ST-LINK |
| Serial program | `picocom -b 115200 --logfile boot.log /dev/ttyACM0` (leave with `Ctrl-A`, `Ctrl-X`). Check the port name with `dmesg` after plugging the USB cable in; close ModemManager-like programs that grab ports |
| Boot switch | set for **SD card** ([07](07-flashing-and-booting.md#2-set-the-board-to-boot-from-the-sd-card)) |
| Card | written with `./build.sh flash -d /dev/sdX` (which also wipes the U-Boot environment area) |
| More BL2 output | the default log level 20 hides BL2's INFO lines. For a first boot, put `TFA_LOG_LEVEL=40` into `config/local.conf`, then `./build.sh firmware tfa` and `./build.sh firmware fip` before `image`, or run `./build.sh --yes flash -d /dev/sdX --firmware-only` after rebuilding |
| Start logging **before** you apply power | the first lines are the ones that tell you most |

```bash
echo 'TFA_LOG_LEVEL=40' > config/local.conf     # first boot only; remove it afterwards
rm -rf build/work/tf-a && ./build.sh firmware tfa && ./build.sh firmware fip && ./build.sh image
```

## 2. What to capture and how

Send back (or keep for yourself) **all** of these. Do not paraphrase and do not send a screenshot: the exact
characters matter.

1. The **complete raw log from power-on** to the login prompt, or to wherever it stopped: the file `boot.log`
   from `picocom --logfile`. Include a power cycle so the log starts at the first line the ROM-loaded BL2 prints.
2. `./build.sh info` (the exact versions and options of the build) and `git rev-parse HEAD` of this repository.
3. The card's partition table, on your PC: `sudo sfdisk -d /dev/sdX` and
   `lsblk -o NAME,PARTLABEL,PARTUUID /dev/sdX`.
4. If you reached U-Boot's prompt (press a key during the countdown): `printenv`, `mmc list`, `mmc info`,
   `part list mmc 0`, `ls mmc 0:5 /boot`, and `bdinfo`.
5. If Linux started: `dmesg` (or the part of the log you have), `cat /proc/cmdline`, `lsblk`, `ip -br a`.
6. `build/deploy/` listing with sizes (`ls -l build/deploy`) and the `fiptool info` output of `fip.bin`
   (`./build.sh firmware fip` prints it).

## 3. A good boot, stage by stage

Times are not given because none were measured on hardware. `LOG_LEVEL=40` adds the `INFO:` lines.

| Stage | Lines you should see | Printed by |
| --- | --- | --- |
| **ROM** | nothing: the ROM does not print | |
| **BL2** (at least) | `NOTICE:  CPU: STM32MP157F…` (the chip name and revision), `NOTICE:  Model: STMicroelectronics STM32MP157F-DK2 Discovery Board`, `NOTICE:  Board: MB…… Var… Rev.…-…`, `NOTICE:  BL2: v2.15.0(release):da738d5`, `NOTICE:  BL2: Built : …`, `NOTICE:  BL2: Booting BL32` | `plat/st/stm32mp1/stm32mp1_private.c`, `bl2_plat_setup.c`, `bl2/bl2_main.c` |
| BL2 at level 40 | `INFO:    Reset reason (0x…):` plus `Power-on Reset (rst_por)`, then `INFO:    Loading image id=… at address 0x…` for the images | `bl2_plat_setup.c`, `common/bl_common.c` |
| **OP-TEE** | `I/TC: Early console on UART#4`, `I/TC: OP-TEE version: 4.11.0 …`, `I/TC: WARNING: This OP-TEE configuration might be insecure!` (expected: this is a development build, `CFG_INSECURE=y`), `I/TC: Primary CPU initializing`, `I/TC: Platform stm32mp1: flavor … - DT stm32mp157c-dk2-scmi.dts`, `I/TC: Primary CPU switching to normal world boot` | `core/arch/arm/kernel/boot.c`, `plat-stm32mp1/main.c` |
| **U-Boot** | `U-Boot 2026.07 (…)`, `CPU: STM32MP157F…`, `Model: STMicroelectronics STM32MP157C-DK2 SCMI Discovery Board` (the C-variant tree: see [03](03-firmware-and-uboot.md#step-2-u-boot)), `Board: stm32mp1 in trusted mode (st,stm32mp157c-dk2-scmi)`, `DRAM:  512 MiB`, `Net:`, `Hit any key to stop autoboot:  1`, then `Boot over mmc0!` | `board/st/stm32mp1/stm32mp1.c`, `common/autoboot.c`, `stm32mp15_st_common.h` |
| **extlinux** | `Scanning mmc 0:5...`, `Found /boot/extlinux/extlinux.conf`, `Retrieving file: /boot/extlinux/extlinux.conf`, `Boot menu`, `1:	Linux`, `2:	Linux, verbose …`, `Retrieving file: /boot/zImage`, `append: root=PARTUUID=6d703135-… console=ttySTM0,115200 rootwait rw earlycon`, `Retrieving file: /boot/stm32mp157f-dk2.dtb`, `Starting kernel ...` | `include/config_distro_bootcmd.h`, `boot/pxe_utils.c` |
| **Kernel** | `Booting Linux on physical CPU 0x0`, `Linux version 6.18.58-custom …`, `Machine model: STMicroelectronics STM32MP157F-DK2 Discovery Board`, `optee: revision 4.11 …`, `arm-scmi … SCMI Protocol v… 'STM:…' Firmware version 0x…`, `mmc0: new high speed SDHC card at address …` (the exact wording varies with the card), `EXT4-fs (mmcblk0p5): mounted filesystem …`, `VFS: Mounted root (ext4 filesystem) …` | `drivers/of/fdt.c`, `drivers/tee/optee/smc_abi.c`, `drivers/firmware/arm_scmi/base.c`, `drivers/mmc/core/`, `fs/ext4` |
| **Userland** | Debian: `Welcome to Debian GNU/Linux 13 (trixie)!`, then `stm32mp157f-dk2 login:`. Alpine: `Welcome to Alpine Linux`, then the same `login:`. Log in as `root` or `dev`, password `stm32mp1` | systemd / BusyBox |

Two things that are **normal** and should not alarm you: the `WARNING: This OP-TEE configuration might be
insecure!` lines, and (with a card that was used before) U-Boot saying it created a new environment.

## 4. If it does not boot: the first line that identifies each failure

Look for the **first** line in the table that matches your log, from the top. The "fix" column points at the
chapter with the details.

| What you see (first identifying line) | Meaning | Look at |
| --- | --- | --- |
| nothing at all, not even from BL2 | wrong serial port or settings; boot switch not on SD; card not seated; the ROM did not find `fsbl1` | [09](09-troubleshooting.md#board-time-nothing-on-the-console); try the card in `sfdisk -d` first |
| garbage characters | wrong baud rate (must be 115200) | serial settings above |
| `NOTICE:  CPU: …` then nothing | BL2 stopped in its set-up; rebuild with `TFA_LOG_LEVEL=40` and send the log | [09](09-troubleshooting.md#bl2-starts-then-stops) |
| `ERROR:   Secure chip: TRUSTED_BOARD_BOOT must be enabled` | the chip is a *closed* device | [03](03-firmware-and-uboot.md#step-4-the-fip) |
| `ERROR:   Invalid DDR init: error …` | the DDR3 set-up failed | [09](09-troubleshooting.md#bl2-starts-then-stops) |
| `ERROR:   PMIC voltages init failed` | BL2 cannot talk to the STPMIC1 | [09](09-troubleshooting.md#bl2-starts-then-stops) |
| `ERROR:   SDMMC1 init failed` | BL2 cannot read the card | re-seat or replace the card |
| `ERROR:   Could NOT find the fip partition!` | no partition of the FIP type GUID or named `fip` | `sfdisk -d` must show `fip` with type `19D5DF83-…` |
| `ERROR:   BL2: Failed to load image id …` | the FIP lacks a file BL2 wants, or was truncated | `fiptool info` of the partition's contents |
| `ERROR:   OPTEE header parse error.` | the BL32 file is not an OP-TEE header | the FIP was built from the wrong files |
| `NOTICE:  BL2: Booting BL32`, then nothing | OP-TEE did not start | [09](09-troubleshooting.md#op-tee-starts-u-boot-does-not) |
| `I/TC: Primary CPU switching to normal world boot`, then nothing | U-Boot did not start (no console in U-Boot: wrong U-Boot tree?) | [09](09-troubleshooting.md#op-tee-starts-u-boot-does-not), [03](03-firmware-and-uboot.md#step-2-u-boot) |
| U-Boot banner, then `STM32MP>` prompt after the countdown | U-Boot found nothing to boot | [09](09-troubleshooting.md#u-boot-starts-but-linux-does-not): `part list mmc 0` must show the rootfs bootable |
| `Starting kernel ...` then nothing | the kernel does not start or has no console | [09](09-troubleshooting.md#linux-prints-nothing-after-starting-kernel-): is it the `zImage` of this build and `stm32mp157f-dk2.dtb`? |
| `Waiting for root device PARTUUID=…` | the SD controller did not probe | [09](09-troubleshooting.md#linux-never-finds-the-root-filesystem): use the `linux-debug` entry, read `deferred probe pending:` |
| `VFS: Unable to mount root fs` with `Unknown parameter` | a `rootflags=` crept into the command line | [09](09-troubleshooting.md#kernel-panic-with-an-ext4-unknown-parameter-message) |
| login prompt, but no network | cable, DHCP, or driver | [09](09-troubleshooting.md#no-network) |

The U-Boot boot menu has two entries, `1: Linux` (default, chosen after the one-second `TIMEOUT 10`) and
`2: Linux, verbose` (`loglevel=7`, `deferred_probe_timeout=5`). When `1` fails, power-cycle, press a key at
`Enter choice:` and type `2`; or edit `/boot/extlinux/extlinux.conf` on the card (your PC can mount the ext4
partition) to make the verbose entry the default.

Next: back to the [docs index](README.md).
