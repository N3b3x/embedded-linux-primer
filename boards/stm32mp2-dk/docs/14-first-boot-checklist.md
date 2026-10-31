# 14 · First-boot checklist

Nothing in this repository has run on a physical STM32MP257F-DK yet. This chapter is for the day it does: what
to set up, what each stage prints when it works, what its absence means, and exactly what to send back when
it does not. It applies to both stacks ([15](15-two-stacks.md)); where the text differs, the table says so.

## 1. Before you power on

| Check | Why |
| --- | --- |
| **Boot switches set to SD card.** The position is in ST's user manual for the kit; look it up, do not copy it from a photo | A wrong setting makes the Boot ROM look at the on-board eMMC (or at the USB/serial download mode) and print nothing from your card |
| **The card was written by `./build.sh flash`**, not copied | The flash step erases the U-Boot environment area. A card that held another image keeps that image's saved variables otherwise, because the flash tools skip blocks of zeros |
| **A real 5 V / 3 A USB-C supply** on the power connector | A weak supply browns out during DDR training and looks like a dead board |
| **The USB cable in the ST-LINK connector**, not the other USB ports | Only the ST-LINK carries the console (USART2). The HDMI/LVDS outputs show nothing from this build |
| Serial settings **115200 8N1, no flow control** | Hardware flow control on makes some terminals send nothing and print nothing |

Seeing an *ST Linux* (OpenSTLinux) login instead of yours means the board booted its **eMMC**, which ships with
ST's image: the switches are not on SD.

### Capture the serial port to a file from the first byte

You will want the complete log, not a screenshot. Start the capture **before** you apply power:

```bash
picocom -b 115200 --logfile boot.log /dev/ttyACM0         # Linux; leave with Ctrl-A, Ctrl-X
screen -L -Logfile boot.log /dev/cu.usbmodem1103 115200   # macOS (the device name varies)
```

The port is usually `/dev/ttyACM0` on Linux, `/dev/cu.usbmodem…` on macOS and `COMn` on Windows. Close other
programs that hold it. Press the reset button (or unplug and replug the power) with the capture running.

## 2. If the first boot is silent

Work through this in order. The point is to find out whether the problem is the board and its set-up, or the
software, with as few changes as possible.

1. **Nothing at all, not even one line.** Check the three things above (switches, USB cable in the ST-LINK
   port, serial settings and port). Try a second terminal program. Replug the cable *after* opening the port.
2. **Build the other stack and try that card.** `./build.sh -s st all`, flash, boot. If ST's stack prints BL2 and
   reaches a login, the board, switches, card reader and serial cable are fine and the fault is in the
   mainline stack; send the mainline log (section 5). If it is silent too, the fault is shared:
   go to 3.
3. **Rebuild with more BL2 output** (the ST stack already has it):
   `echo 'TFA_LOG_LEVEL=40' >> config/local.conf`, then `./build.sh firmware && ./build.sh image`, flash again
   (`--firmware-only` is enough for BL2 and the FIP). With level 40 the first thing BL2 says is
   `INFO:    Boot used partition fsbl1`.
4. **Still nothing**: the Boot ROM did not find or accept BL2. Check the card in your PC:
   `sudo sfdisk -d /dev/sdX` must list the partitions of your stack with exactly these names
   ([06](06-sdcard-image.md)). If the layout looks right, try the other card layout: ST's puts BL2 at sector 34
   (`-s st`), the mainline one at sector 2048. Try a different, smaller (8 or 16 GB) card.
5. **Text, but it stops.** Find the last line in the table below and follow the right-hand column.

## 3. What each stage prints, and what its absence means

Strings come from the pinned sources; the versions differ between the stacks and are shown where they do.
Lines marked *(level 40)* need `TFA_LOG_LEVEL=40` on the mainline stack (the ST stack builds at 40).

| Stage | The line that proves it passed | If it is missing |
| --- | --- | --- |
| **Boot ROM → BL2** | `NOTICE:  CPU: STM32MP257…` and `NOTICE:  Model: STMicroelectronics STM32MP257F-DK …`, then `NOTICE:  BL2: v2.15.0…` (mainline) or `BL2: v2.10-stm32mp2…` (st). *(level 40)* `INFO:    Boot used partition fsbl1` | Nothing at all: switches, cable, supply (section 1), or the ROM rejected BL2: look at the partition names. `fsbl2` in that line means the first copy was bad and the fallback was used |
| **DDR and the FIP** | no `ERROR:` between BL2's banner and `BL31:`. *(level 40)* `INFO:    Loading image id=…` for each of the FIP's images | `Could NOT find the fip partition!` (mainline): the type GUID or name is wrong. `Unable to find metadata partition "metadata1"`, `No partition with the uuid mentioned in metadata` (st): the metadata or the `fip-a` PARTUUID is wrong. A `DDR` error: the DDR settings or firmware do not match the board |
| **BL31** | `NOTICE:  BL31: v2.15.0…` (mainline) or `BL31: v2.10-stm32mp2…` (st) | Stops after BL2's last line: BL2 could not hand over, usually a bad image in the FIP: `fiptool info` on your `fip.bin` |
| **OP-TEE** | `I/TC: Primary CPU initializing`, `I/TC: OP-TEE version: 4.11.0…` (mainline) or `4.0.0…` (st), `I/TC: Primary CPU switching to normal world boot` | Silence after `BL31:`, or an `E/TC:` or `ERROR:` line: OP-TEE failed to start (firewall setup, PMIC, memory map). Send the whole log; this is the stage where the two stacks differ most |
| **U-Boot** | `U-Boot 2026.07…` (mainline) or `U-Boot 2023.10-stm32mp-r3…` (st), a `Model:` line, `Boot over mmc0!` | Stops after OP-TEE's last line: BL31 could not start U-Boot, or U-Boot died early. On the mainline stack a few `scmi_regulator … Failed to query voltage domain` lines are expected (OP-TEE 4.11 has no voltage domain); they are not a failure by themselves |
| **SD card in U-Boot** | `Scanning mmc 0:…` (mainline `0:5`, st `0:8`) | No `mmc0` or `Card did not respond`: the card or its supply. At the `STM32MP>` prompt: `mmc dev 0; mmc info; part list mmc 0` and send the output |
| **extlinux** | `Found /boot/extlinux/extlinux.conf`, a boot menu for a moment, then `Retrieving file: /boot/Image`, `Retrieving file: /boot/….dtb`, `append: root=PARTUUID=…` | `Unable to read file`, or it falls through to other boot targets: the bootable flag is missing or the files are not in `/boot` of the bootable partition |
| **Kernel starts** | `Booting Linux on physical CPU 0x0` and the banner `Linux version 6.18.58-custom` (mainline) or `6.6.116-custom` (st), `Machine model: STMicroelectronics STM32MP257F-DK …`. With `earlycon`, lines appear *before* the normal console takes over | Silence after `Starting kernel ...`: the kernel never got going. `earlycon` should still print: if even that is silent, the device tree or the load addresses are wrong. Send the log |
| **SD card in Linux** | `mmc0: new … SDHC card` and `EXT4-fs (mmcblk0p…): mounted filesystem`, `VFS: Mounted root` | `Waiting for root device PARTUUID=…` and no `mmc0` line: the SD controller never probed. On the mainline stack this is the SCMI supply problem ([09](09-troubleshooting.md#linux-never-finds-the-root-filesystem)): in the boot menu choose the other device tree and compare. `platform 48220000.mmc: deferred probe pending` confirms it |
| **Userland** | `Reached target`, `stm32mp257f-dk login:` on `ttySTM0`; `ip a` shows `end0` | systemd or getty problems: boot with `init=/bin/sh` appended to the `APPEND` line to see whether the root filesystem itself is fine |

### The U-Boot boot menu

`extlinux.conf` waits 3 seconds, and with the mainline stack it has two entries: the default
`stm32mp257f-dk-primer.dtb` (fixed SD supplies) and `stm32mp257f-dk.dtb` (the stock tree). Press a key on the
serial console while the menu shows and choose the second one to compare. The first-boot question "does my
workaround make the difference?" is answered by which entry reaches `mmc0: new … card`.

## 4. The order I would try things in

1. `./build.sh -s st all`, flash, boot. This is the stack whose versions and device trees a bench-proven
   configuration booted on this very kit.
2. If it works: build and flash the mainline card, boot it with the capture running. A login means both
   stacks work; a failure is then a mainline-stack failure and the log says where.
3. If the mainline card stops, try its second boot-menu entry, then `TFA_LOG_LEVEL=40`.
4. If ST's stack is silent: switches, cable and supply first; then try the `fsbla1`-at-sector-2048 mainline layout
   to see whether the layout matters.

## 5. What to send back

Always the **complete raw log from power-on** (the capture file), plus:

```bash
git rev-parse HEAD                  # which version of this repository
./build.sh info                     # (or ./build.sh -s st info) what was built
sudo sfdisk -d /dev/sdX             # the card's table, from your PC
lsblk -o NAME,PARTLABEL,PARTUUID /dev/sdX
```

If you reached the `STM32MP>` prompt (press a key during the 1-second `Hit any key to stop autoboot` countdown), add:

```text
STM32MP> printenv
STM32MP> mmc dev 0 ; mmc info
STM32MP> part list mmc 0
```

If BL2 or OP-TEE stopped, also send the output of `fiptool info build/deploy*/fip.bin` (the tool is in
`build/src*/trusted-firmware-a/tools/fiptool/`). For a kernel that stops, the `earlycon` lines are what to send.

## 6. Things that are not failures

* The mainline stack's U-Boot reports `Failed to query voltage domain` for the SD supplies, then reads the card
  anyway at 3.3 V ([11](11-secure-world-and-scmi.md)). Expected, not verified on hardware.
* The first boot of either stack writes U-Boot's environment into `u-boot-env` (`env save` inside `bootcmd`).
* `systemd-timesyncd` starts in 1970 until a network is up ([09](09-troubleshooting.md#slow-or-wrong-time)).
* On a mainline kernel no display, USB, audio, Wi-Fi or Cortex-M33 will work ([12](12-board-tour.md)). ST's 6.6 tree
  enables more peripherals in its device tree, but this image ships no drivers' user space for them.

Next: [15 · The two stacks](15-two-stacks.md).
