# 07 · Flashing the card and booting the board

> **Status of this chapter.** The image was assembled and inspected on a PC; it has **not yet been booted on
> a physical STM32MP157F-DK2** by the authors of this repository. The boot-switch positions come from U-Boot's
> documentation in the pinned source tree, not from an ST page (which could not be fetched): check them
> against the kit's user manual. Where this chapter says "you should see", the text was taken from the source
> code that prints it.

## 1. Write the card

You need a microSD card (8 GB or more is comfortable: the Debian image is a few GB) and a card reader.
**Everything on the card is erased.**

```bash
lsblk -dpo NAME,SIZE,TRAN,MODEL            # find the card: look at SIZE and MODEL
./build.sh flash -d /dev/sdX --expand      # X = your card; not a partition (sdX1), the whole disk
```

`scripts/flash.sh` refuses to write unless:

* the target is a whole **block device**, not a partition;
* none of its partitions is mounted as `/`, `/boot`, `/home`, `/usr`, `/var` or swap;
* it is removable, USB or `mmcblk`, and no larger than 256 GB (`--force` overrides, be sure);
* **you confirm** after it has shown the disk's model and size.

Then it unmounts anything the desktop mounted for you and writes `build/deploy/sdcard.img`: with
`bmaptool copy` if `bmaptool` is installed (it writes only the blocks that hold data, and verifies them),
else with `dd bs=4M conv=fsync`. Because `bmaptool` skips blocks of zeros, `flash.sh` then **zeroes the whole
`u-boot-env` partition**, so that an environment saved on that card by an older image (ST's, or an earlier
build of this board) cannot survive and override the boot command. `--expand` finally grows the rootfs partition and its ext4 filesystem to
fill the whole card (the image itself is only as large as its content).

### Other ways to write the same file

The image is a normal raw disk image, so any tool works. Replace `sdX`:

```bash
sudo bmaptool copy --bmap build/deploy/sdcard.img.bmap build/deploy/sdcard.img /dev/sdX
sudo dd if=build/deploy/sdcard.img of=/dev/sdX bs=4M conv=fsync status=progress
```

or balenaEtcher on Windows/macOS. After a manual write the rootfs is small; grow it on the board:

```bash
sudo sfdisk --no-reread -N 5 /dev/mmcblk0 <<< ', +'       # on the board; check the device name first
sudo partprobe /dev/mmcblk0 && sudo resize2fs /dev/mmcblk0p5
```

### Updating one part of a card you already wrote

```bash
./build.sh flash -d /dev/sdX --firmware-only   # rewrite BL2 (fsbl1, fsbl2) and the FIP only
./build.sh flash -d /dev/sdX --kernel-only     # replace /boot/zImage, the DTB and /lib/modules
```

Both first check that the card carries *this* repository's partition names (`fsbl1`, `fsbl2`, `fip`,
`u-boot-env`, `rootfs`) and stop otherwise.

## 2. Set the board to boot from the SD card

The Boot ROM decides where to boot from by reading **boot pins**. On the DK1/DK2 kits two of them (BOOT0 and
BOOT2) are set by the switch `SW1` (BOOT1 is wired low). The table below is the one in U-Boot's own
documentation, `doc/board/st/stm32mp1.rst` of the pinned tree (section "Switch Setting for Boot Mode"); the ST
wiki page for the kit could not be fetched while this chapter was written, so **check it against the kit's user
manual** on st.com before relying on it:

| Boot mode | BOOT2 | BOOT0 |
| --- | --- | --- |
| Recovery (serial / USB download) | 0 | 0 |
| (NOR: not applicable) | 0 | 1 |
| Reserved | 1 | 0 |
| **SD card** | **1** | **1** |

A wrong setting leaves the board silent or in recovery mode, which is harmless: move the switch and power-cycle.
The same document says: "To boot from SD card, select BootPinMode = 1 0 1 and reset" (BOOT2, BOOT1, BOOT0).

* ST's page for the kit has the **user manual** and the **quick-start guide**: search for
  "STM32MP157F-DK2" on st.com.
* Make sure the card is fully inserted in the **microSD** slot. The kit has no eMMC.

## 3. Connect the serial console

Plug the kit's debug USB connector (the one that powers and exposes the on-board ST-LINK; see
[12 · Board tour](12-board-tour.md)) into your PC and open the serial port at **115200 8N1**:

```bash
sudo picocom -b 115200 /dev/ttyACM0          # leave: Ctrl-A, Ctrl-X
```

The console is **UART4** (`serial0` in the device tree, `ttySTM0` in Linux, at `0x40010000`). The same UART
carries, in order: BL2's messages, OP-TEE's, U-Boot's, then the kernel's, then the login prompt, so one
terminal is enough. Use **8N1 and no flow control**; with `picocom` add `--logfile boot.log` to keep the boot.

## 4. Power on and what to look for

Power the board (the kit's power input; see [12](12-board-tour.md)). To see more of what BL2 does, rebuild it
with a higher log level and write the card again:

```bash
rm -rf build/work/tf-a
TFA_LOG_LEVEL=40 ./build.sh firmware tfa && ./build.sh firmware fip && ./build.sh image
./build.sh flash -d /dev/sdX --firmware-only      # no need to rewrite the whole card
```

Milestones, and where each string comes from (the complete list, with the failure each missing line means,
is in [15 · First boot checklist](15-first-boot-checklist.md)):

| You should see | From | It means |
| --- | --- | --- |
| `NOTICE:  CPU: STM32MP157F…`, `NOTICE:  Model: STMicroelectronics STM32MP157F-DK2 Discovery Board`, `NOTICE:  BL2: v2.15.0(release):…`, `NOTICE:  BL2: Booting BL32` | `plat/st/stm32mp1/stm32mp1_private.c`, `bl2/bl2_main.c` | the ROM found `fsbl1` and BL2 is running; it loaded the FIP |
| `I/TC: OP-TEE version: 4.11.0 …`, `I/TC: Primary CPU switching to normal world boot` | `core/arch/arm/kernel/boot.c` | OP-TEE is up |
| U-Boot banner, then `Boot over mmc0!` (the number is `boot_instance`) | `include/configs/stm32mp15_st_common.h` | OP-TEE started U-Boot; it knows it booted from an SD card |
| `Scanning mmc 0:5...`, `Found /boot/extlinux/extlinux.conf`, `Retrieving file: /boot/zImage` | `include/config_distro_bootcmd.h`, `boot/pxe_utils.c` | the bootable partition was found and read |
| `Machine model: STMicroelectronics STM32MP157F-DK2 Discovery Board` | `drivers/of/fdt.c` (value from the DTB) | the kernel started and parsed the device tree |
| `optee: revision 4.11` | `drivers/tee/optee/smc_abi.c` | Linux's driver reached OP-TEE |
| `SCMI Protocol v… '<vendor>:<sub-vendor>' Firmware version 0x…` | `drivers/firmware/arm_scmi/base.c` | the SCMI link works ([11](11-secure-world-and-scmi.md)) |
| `stm32mp157f-dk2 login:` | systemd (hostname from `TARGET_HOSTNAME`) | done: `root` / `dev`, password `stm32mp1` |

If a milestone is missing, [09 · Troubleshooting](09-troubleshooting.md) is organised by the last line you
*did* see.

### The first thing to try once logged in

```bash
uname -a                        # Linux stm32mp157f-dk2 6.18.58-custom … armv7l
cat /proc/device-tree/model     # the DK2's model string
ip -br a                        # end0 gets an address by DHCP when a cable is connected
lsblk -o NAME,SIZE,PARTLABEL    # your five partitions
sudo dmesg | grep -iE 'optee|scmi'
```

## 5. Recovery: when the board will not boot from the card

With the switch in the **Recovery** position (above) the Boot ROM waits for a **serial or USB download**, which
lets a PC load firmware without any card, with ST's **STM32CubeProgrammer**. It is the way back from a card that
does not boot. This repository does not script it: follow ST's STM32CubeProgrammer documentation for the
STM32MP15 and use the files in `build/deploy/` (BL2 as the first-stage loader, the FIP as the second). BL2
here is built for SD boot only (`STM32MP_SDMMC=1`); a serial-download BL2 would need `STM32MP_UART_PROGRAMMER=1`
or `STM32MP_USB_PROGRAMMER=1` instead ([09](09-troubleshooting.md#tf-a-the-build-runs-out-of-sysram)).

Next: [08 · Customizing](08-customizing.md).
