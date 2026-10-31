# 07 · Flashing the card and booting the board

> **Status of this chapter.** The image was assembled and inspected on a PC, and its kernel, root filesystem and
> U-Boot distro boot were run in the QEMU model of a Zynq-7000 (see the status table in the [README](../README.md)).
> It has **not yet been booted on a physical Eclypse Z7** by the authors of this repository. Jumper and connector
> positions below are quoted from Digilent's reference manual; the console text marked *(QEMU)* was captured from
> a run, the text marked *(source)* is what the source code prints. Use [14 · First-boot checklist](14-first-boot-checklist.md)
> when you try it and capture a log.

## 1. Write the card

You need a microSD card (8 GB or more is comfortable: the Debian image is 1.3 GB) and a card reader.
**Everything on the card is erased.**

```bash
lsblk -dpo NAME,SIZE,TRAN,MODEL            # find the card: look at SIZE and MODEL
./build.sh flash -d /dev/sdX --expand      # X = your card; not a partition (sdX1), the whole disk
```

`scripts/flash.sh` refuses to write unless:

* the target is a whole **block device**, not a partition;
* none of its partitions is mounted as `/`, `/boot`, `/boot/efi`, `/home`, `/usr`, `/var` or swap;
* it is removable, USB or `mmcblk`, and no larger than 256 GB (`--force` overrides, be sure; `--force` also allows a loop device, which is how the script was tested);
* **you confirm** after it has shown the disk's model and size.

Then it unmounts anything the desktop mounted for you and writes `build/deploy/sdcard.img`: with `bmaptool copy`
if `bmaptool` is installed (only the blocks that hold data, verified), else with `dd bs=4M conv=fsync`. `--expand`
finally grows the ext4 partition (partition 2) and its file system to the whole card.

### Other ways to write the same file

The image is a plain raw disk image, so any tool works:

```bash
sudo bmaptool copy --bmap build/deploy/sdcard.img.bmap build/deploy/sdcard.img /dev/sdX
sudo dd if=build/deploy/sdcard.img of=/dev/sdX bs=4M conv=fsync status=progress
```

or balenaEtcher on Windows/macOS. After a manual write the root partition is small; grow it on the board:

```bash
sudo sfdisk --no-reread -N 2 /dev/mmcblk0 <<< ', +'       # on the board; check the device name first
sudo partprobe /dev/mmcblk0 && sudo resize2fs /dev/mmcblk0p2
```

### Updating one part of a card you already wrote

```bash
./build.sh flash -d /dev/sdX --firmware-only   # new BOOT.BIN and u-boot.img on the FAT partition
./build.sh flash -d /dev/sdX --kernel-only     # new zImage + DTB (FAT) and modules (ext4)
```

Both first check that the card has this build's layout: partition 1 is `vfat` labelled `BOOT`, partition 2 `ext4`
labelled `rootfs`. They use `mcopy` on the device (no mounting) for the FAT files.

## 2. Set the board up

The reference for the board is Digilent's *Eclypse Z7 Reference Manual* (section 2, *Boot modes*). The facts used
here are:

| Item | What | Where |
| --- | --- | --- |
| **Boot jumper** | **JP5**, three positions: `JTAG` (two leftmost pins shorted), `QSPI` (two centre pins), **`SD` (two rightmost pins shorted, labelled "SD")**. Put **one** jumper on the two pins nearest the SD label | next to the board's sticker with the MAC address, above the headphone jack |
| Power | 12 V barrel jack **J11** and the **power switch** (ON) | the board has a power switch; the card is read at power-on |
| microSD | slot **J4**, labelled "SD CARD", on the underside of the board | insert the card until it clicks |
| Serial console | micro-USB **J6**, "USB JTAG/UART", an FTDI **FT2232HQ** | channel B is the UART (115200 8N1, UART0 on MIO 14/15) |
| Ethernet | RJ45 J3, RTL8211E PHY, link LED steady on = link | optional for the first boot |
| Reset | BTNR (underside, below the SD slot) resets the Zynq but **does not re-read JP5** | a changed jumper needs a power cycle |

**Power-cycle after any jumper change.** The mode pins are latched only at power-on.

## 3. Connect the serial console

Plug a micro-USB cable from J6 to your PC. The FTDI chip has two channels: the first is the JTAG interface, the
second is the serial port. On Linux you get two devices, `/dev/ttyUSB0` and `/dev/ttyUSB1`, and the serial port is
the **second one** (`ls -l /dev/serial/by-id/` shows `…-if01-port0`). If another USB serial adapter was plugged in
first, the numbers shift: use the by-id name. On macOS the console is the second `/dev/cu.usbserial-…` device.

```bash
sudo picocom -b 115200 --logfile boot.log /dev/ttyUSB1          # leave: Ctrl-A, Ctrl-X
```

Facts: 115200 baud, 8 data bits, no parity, 1 stop bit, no flow control. The same UART carries, in order, the SPL's
messages, U-Boot's, the kernel's, and the login prompt: one terminal is enough.

The FT2232HQ is powered by the board, so the USB devices appear only after you turn the board on and **disappear
and reappear on every power cycle**. To catch the first line of the SPL, start the terminal in a loop that
waits for the port and reconnects:

```bash
while [ ! -e /dev/ttyUSB1 ]; do sleep 0.1; done; sudo picocom -b 115200 --logfile boot.log /dev/ttyUSB1
```

Run it, then flip the power switch.

## 4. Power on and what to look for

Milestones, in order, and where each text comes from:

| You should see | From | It means |
| --- | --- | --- |
| *(nothing, then)* `U-Boot SPL 2026.07-eclypse-z7-… (date)` | *(source)* `common/spl/spl.c`, `CONFIG_SPL_BANNER_PRINT` | the BootROM loaded `BOOT.BIN`; `ps7_init` and the UART worked |
| `Silicon version: 3` (the number depends on the chip revision) | *(source)* `board/xilinx/zynq/board.c` | the SPL's `board_init()` ran |
| `Trying to boot from MMC1` | *(source)* `common/spl/spl.c` | the SPL is reading the SD card |
| `U-Boot 2026.07-eclypse-z7-… (date)` `Model: Digilent Eclypse Z7` `DRAM:  ECC disabled 1 GiB` | *(QEMU)* | U-Boot proper is running from DDR, and it sees 1 GiB |
| `MMC:   mmc@e0100000: 0` | *(QEMU)* | the SD host driver |
| `Hit any key to stop autoboot:  2` | *(QEMU)* | press a key here to get the `Zynq>` prompt |
| `Scanning mmc 0:1…` `Found /extlinux/extlinux.conf` | *(QEMU)* | distro boot found the file on partition 1 |
| `Retrieving file: /zImage` `Retrieving file: /zynq-eclypse-z7.dtb` `Starting kernel ...` | *(QEMU)* | kernel and device tree loaded, `bootz` jumped |
| `Booting Linux on physical CPU 0x0` `Machine model: Digilent Eclypse Z7` | *(QEMU)* | the kernel started and read the device tree |
| `mmc0: new high speed SD card` `mmcblk0: p1 p2` | *(QEMU)* | the root device exists |
| `VFS: Mounted root (ext4 filesystem) on device 179:2.` `Run /sbin/init as init process` | *(QEMU)* | root mounted |
| `Debian GNU/Linux 13 eclypse-z7 ttyPS0` `eclypse-z7 login:` | *(QEMU)* | done: `root` / `dev`, password `zynq7000` |

On the real board, expect also: `Net:   ZYNQ GEM: e000b000, mdio bus e000b000, phyaddr 1, interface rgmii-id`
(U-Boot) and `macb e000b000.ethernet eth0: Cadence GEM rev … at 0xe000b000 irq …` then
`macb … end0: PHY [e000b000.ethernet-ffffffff:01] driver [RTL8211E Gigabit Ethernet]` (kernel). In QEMU there is no
PHY, so these lines read *"Could not get PHY"* instead. The `GIC CPU mask not found` line is also a QEMU artefact.

If a milestone is missing, [09 · Troubleshooting](09-troubleshooting.md) and the table in
[14 · First-boot checklist](14-first-boot-checklist.md) are organised by the last line you *did* see.

### The first thing to try once logged in

```bash
uname -a                         # Linux eclypse-z7 6.18.58-custom … armv7l
cat /proc/device-tree/model      # Digilent Eclypse Z7
ip -br a                         # end0 gets an address by DHCP when a cable is connected
lsblk -o NAME,SIZE,FSTYPE,LABEL  # mmcblk0p1 BOOT (vfat), mmcblk0p2 rootfs (ext4)
cat /proc/cpuinfo | grep -c processor   # 2
dmesg | grep -iE 'mmc0|macb|fpga'
cat /sys/class/fpga_manager/fpga0/state   # unknown: the PL has no configuration (needs fpga_manager loaded, chapter 13)
```

## 5. Recovery: when the board will not boot from the card

* **JTAG.** Digilent's USB-JTAG on the same connector (the first FTDI channel) can load code into a board whose
  card does not boot: Xilinx's tools (Vivado Hardware Manager, `xsct`) or OpenOCD. This repository does not script
  it.
* **QSPI.** The board's 16 MB flash can hold a boot image (JP5 on `QSPI`). A factory image may still be there:
  with JP5 on `QSPI` the board boots *that*, which is a useful check that the board, power and UART work at all.
  This build never writes the flash.
* **A card that does not boot:** write it again, re-read [14](14-first-boot-checklist.md), and compare the first
  bytes of the FAT partition with the image (chapter [06](06-sdcard-image.md#how-the-image-is-made-rootless)).

Next: [08 · Customizing](08-customizing.md).
