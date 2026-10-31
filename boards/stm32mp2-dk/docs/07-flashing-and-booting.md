# 07 · Flashing the card and booting the board

> **Status of this chapter.** The images were assembled and inspected on a PC, and `flash.sh` was run against a loop
> device; nothing has been **booted on a physical STM32MP257F-DK** by the authors of this repository. Everything about
> the board's switches and LEDs below is therefore pointed at ST's documentation rather than guessed. Where this
> chapter says "you should see", the text was taken from the source code that prints it. A step-by-step list of the
> log lines for each stage, and what to send back if one is missing, is [14](14-first-boot-checklist.md).

## 1. Write the card

You need a microSD card (8 GB or more is comfortable: the Debian image is a few GB) and a card reader.
**Everything on the card is erased.**

```bash
lsblk -dpo NAME,SIZE,TRAN,MODEL            # find the card: look at SIZE and MODEL
./build.sh flash -d /dev/sdX --expand      # X = your card; not a partition (sdX1), the whole disk
./build.sh -s st flash -d /dev/sdX --expand   # the same, for the image built with -s st
```

Use the same `-s` as for the build: the flash step writes the image of the selected stack and checks partition
names against that stack's layout.

`scripts/flash.sh` refuses to write unless:

* the target is a whole **block device**, not a partition;
* none of its partitions is mounted as `/`, `/boot`, `/home`, `/usr`, `/var` or swap;
* it is removable, USB or `mmcblk`, and no larger than 256 GB (`--force` overrides, be sure);
* **you confirm** after it has shown the disk's model and size.

Then it unmounts anything the desktop mounted for you and writes `build/deploy/sdcard.img` (`deploy-st/` with
`-s st`): with `bmaptool copy` if `bmaptool` is installed (it writes only the blocks that hold data, and verifies
them), else with `dd bs=4M conv=fsync`.

**It then erases the U-Boot environment partition.** `bmaptool` and sparse images skip blocks of zeros, so the
empty `u-boot-env` of the image is never written; on a card that held another image (ST's, or an older build of
this one) U-Boot's saved variables would survive the flash and be loaded at the first boot. The step finds the
partition by name in the table just written and zeroes it.

`--expand` finally grows the rootfs partition and its ext4 filesystem to fill the whole card (the image itself is
only as large as its content). It uses `sfdisk -N <rootfs>`, which keeps the partition's PARTUUID and bootable
attribute (the script checks both before and after and stops if an `sfdisk` ever disagrees).

### Other ways to write the same file

The image is a normal raw disk image, so any tool works. Replace `sdX`:

```bash
sudo bmaptool copy --bmap build/deploy/sdcard.img.bmap build/deploy/sdcard.img /dev/sdX
sudo dd if=build/deploy/sdcard.img of=/dev/sdX bs=4M conv=fsync status=progress
```

or balenaEtcher on Windows/macOS. A manual write does **not** erase the U-Boot environment: do it yourself
(the `start` and `size` of `u-boot-env` come from `sudo sfdisk -d /dev/sdX`):

```bash
sudo dd if=/dev/zero of=/dev/sdX bs=512 seek=<start> count=<size> conv=fsync   # 18432 and 1024 (mainline), 18466 and 1024 (st)
```

After a manual write the rootfs is small; grow it on the board (the rootfs is partition 5, or 8 with `-s st`):

```bash
sudo sfdisk --no-reread -N 5 /dev/mmcblk0 <<< ', +'       # on the board; check the device name first
sudo partprobe /dev/mmcblk0 && sudo resize2fs /dev/mmcblk0p5
```

### Updating one part of a card you already wrote

```bash
./build.sh flash -d /dev/sdX --firmware-only   # rewrite BL2 (fsbla1, fsbla2) and the FIP only
./build.sh flash -d /dev/sdX --kernel-only     # replace /boot/Image, the DTBs and /lib/modules
```

`--firmware-only` also rewrites the FWU metadata and both FIP partitions with `-s st`. Both modes first check that
the card carries *this stack's* partition names, in order (mainline: `fsbla1 fsbla2 fip u-boot-env rootfs`; st:
`fsbla1 fsbla2 metadata1 metadata2 fip-a fip-b u-boot-env rootfs`) and stop otherwise.

## 2. Set the board to boot from the SD card

The Boot ROM decides where to boot from by reading **boot pins**, which on the Discovery Kit are set by a
small bank of switches. The position for "SD card" is printed on the board and in the kit's user manual;
look it up there rather than here: ST has changed switch conventions between families, and a wrong guess
can leave the board trying to boot from an empty memory.

* ST's page for the kit has the **user manual** and the **quick-start guide**: search for
  "STM32MP257F-DK" on st.com.
* Make sure the card is fully inserted in the **microSD** slot.

## 3. Connect the serial console

Plug the kit's debug USB connector (the one that powers and exposes the on-board ST-LINK; see
[12 · Board tour](12-board-tour.md)) into your PC and open the serial port at **115200 8N1**:

```bash
sudo picocom -b 115200 /dev/ttyACM0          # leave: Ctrl-A, Ctrl-X
```

The console is **USART2** (`serial0` in the device tree, `ttySTM0` in Linux). The same UART carries,
in order: BL2's messages, OP-TEE's, U-Boot's, then the kernel's, then the login prompt, so one terminal
is enough.

## 4. Power on and what to look for

Power the board (the kit's power input; see [12](12-board-tour.md)). Capture the port to a file from before power-on
(`picocom -b 115200 --logfile boot.log /dev/ttyACM0`). To see more of what BL2 does on the mainline stack, rebuild
it with a higher log level (the ST stack is already built at level 40) and write the firmware again:

```bash
echo 'TFA_LOG_LEVEL=40' >> config/local.conf        # (config/local.conf is git-ignored; delete the line afterwards)
./build.sh firmware && ./build.sh image
./build.sh flash -d /dev/sdX --firmware-only       # no need to rewrite the whole card
```

U-Boot waits one second (`Hit any key to stop autoboot`), then the boot menu of `extlinux.conf` shows for three
seconds; with the mainline stack it has two device-tree entries.

Milestones, and where each string comes from:

| You should see | From | It means |
| --- | --- | --- |
| BL2 messages (with log level 40: `Reset reason: Power-on reset …`, `Boot used partition fsbl1`) | `plat/st/stm32mp2/bl2_plat_setup.c`, `plat/st/common/bl2_io_storage.c` | the ROM found `fsbla1` and BL2 is running |
| U-Boot banner, then `Boot over mmc0!` (the number is `boot_instance`) | `include/configs/stm32mp25_st_common.h` | BL2 loaded the FIP; U-Boot knows it booted from an SD card |
| `Scanning mmc 0:5...`, `Found /boot/extlinux/extlinux.conf`, `Retrieving file: /boot/Image` | `include/config_distro_bootcmd.h`, `boot/pxe_utils.c` | the bootable partition was found and read |
| `Machine model: STMicroelectronics STM32MP257F-DK Discovery Board` | `arch/arm64/kernel/setup.c` (value from the DTB) | the kernel started and parsed the device tree |
| `optee: revision 4.11` | `drivers/tee/optee/smc_abi.c` | Linux's driver reached OP-TEE through BL31 |
| `SCMI Protocol v… '<vendor>:<sub-vendor>' Firmware version 0x…` | `drivers/firmware/arm_scmi/base.c` | the SCMI link works ([11](11-secure-world-and-scmi.md)) |
| `stm32mp257f-dk login:` | systemd (hostname from `TARGET_HOSTNAME`) | done: `root` / `dev`, password `stm32mp2` |

If a milestone is missing, [09 · Troubleshooting](09-troubleshooting.md) is organised by the last line you
*did* see.

### The first thing to try once logged in

```bash
uname -a                        # Linux stm32mp257f-dk 6.18.58-custom … aarch64
cat /proc/device-tree/model     # the DK's model string
ip -br a                        # end0 gets an address by DHCP when a cable is connected
lsblk -o NAME,SIZE,PARTLABEL    # your five partitions
sudo dmesg | grep -iE 'optee|scmi'
```

## 5. Recovery: when the board will not boot from the card

The Boot ROM also offers **serial and USB download modes** (listed in
`arch/arm/mach-stm32mp/stm32mp2/cpu.c` as `BOOT_SERIAL_UART` and `BOOT_SERIAL_USB`) which let a PC load
firmware without any card, with ST's **STM32CubeProgrammer**. They are the way back from a card that does
not boot and the way to flash on-board eMMC. This repository does not script them: follow ST's
STM32CubeProgrammer documentation for the STM32MP2 and use the files in `build/deploy/` (BL2 as the
first-stage loader, the FIP as the second).

Next: [08 · Customizing](08-customizing.md).
