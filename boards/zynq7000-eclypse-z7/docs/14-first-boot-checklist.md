# 14 · First-boot checklist

For the day you put the card in the board. The point of this page: if it does not work, **the log you capture tells
which stage failed**, and you can send it to someone who was not there.

> **Honesty box.** Nobody has booted *this* image on a physical Eclypse Z7 yet. What is known:
> the kernel, the Debian root filesystem and U-Boot's distro boot were run in QEMU's Zynq model; the SPL was built, its
> header inspected, and QEMU ran it through `ps7_init`, the UART and SD controller set-up; and a bench-proven
> configuration (the same SPL idea, the same PS7 file, mainline-style U-Boot, a different kernel and rootfs) booted this
> same board. What is **not** known: whether *this* SPL's output appears, whether Ethernet and the SD card behave on
> your board revision, and your card. Lines below are marked *(QEMU)* when captured and *(source)* when taken from the
> code that prints them.

## A. Before power

- [ ] `./build.sh all` finished; `build/deploy/sdcard.img` exists. `sfdisk -d` shows two partitions, the first active.
- [ ] The card is written (`./build.sh flash -d /dev/sdX`) and `mdir -i /dev/sdX1 ::` lists `BOOT.BIN` (131,676 bytes),
      `u-boot.img`, `zImage`, `zynq-eclypse-z7.dtb` and `extlinux`.
- [ ] **JP5 on SD**: one jumper on the two **rightmost** pins, the ones labelled "SD" (reference manual, section 2.1).
- [ ] Card in **J4** ("SD CARD", underside). 12 V in **J11**. Power switch **OFF** for now.
- [ ] micro-USB cable from **J6** to the PC.
- [ ] A terminal logging to a file, waiting for the port (the FTDI appears only when the board has power):

```bash
while [ ! -e /dev/ttyUSB1 ]; do sleep 0.1; done
sudo picocom -b 115200 --logfile boot.log /dev/ttyUSB1
```

  `ttyUSB1` is the **second** FTDI channel (the first is JTAG); check `ls -l /dev/serial/by-id/` (`…-if01-port0`).
  115200 baud, 8N1, **no flow control** (picocom's default). macOS: the second `/dev/cu.usbserial-*`.

## B. Power on and watch

Flip the power switch. Time from power-on, roughly (QEMU for the later stages, so on a real board the kernel
and systemd are faster):

| t | You should see | Stage |
| --- | --- | --- |
| 0 | the serial device appears on the PC | power good, FTDI up |
| < 1 s | `U-Boot SPL 2026.07-eclypse-z7-gece349ade297-dirty (…)` *(source)* | BootROM loaded `BOOT.BIN`; `ps7_init` ran; UART works |
| | `Silicon version: 3` *(source; the number depends on the chip revision)* | SPL `board_init()` |
| | `Trying to boot from MMC1` *(source)* | SPL is reading the card |
| +1 s | `U-Boot 2026.07-eclypse-z7-gece349ade297-dirty (…)` `Model: Digilent Eclypse Z7` `DRAM:  ECC disabled 1 GiB` *(QEMU)* | U-Boot proper; DDR is seen as 1 GiB |
| | `MMC:   mmc@e0100000: 0` `Loading Environment from FAT... OK` *(QEMU: "from SPIFlash", the model's boot mode differs)* | |
| | `Net:   ZYNQ GEM: e000b000, mdio bus e000b000, phyaddr 1, interface rgmii-id` *(source)* | Ethernet MAC and PHY found |
| +3 s | `Hit any key to stop autoboot:  2` *(QEMU)* | press a key to get `Zynq>` |
| | `Scanning mmc 0:1…` `Found /extlinux/extlinux.conf` `Retrieving file: /zImage` `Retrieving file: /zynq-eclypse-z7.dtb` `Starting kernel ...` *(QEMU)* | distro boot |
| +4 s | `Booting Linux on physical CPU 0x0` … `Machine model: Digilent Eclypse Z7` `earlycon: cdns0 at MMIO 0xe0000000` *(QEMU)* | kernel |
| | `smp: Brought up 1 node, 2 CPUs` *(source)* | both Cortex-A9 cores running |
| | `mmcblk0: p1 p2` `EXT4-fs (mmcblk0p2): mounted filesystem` `VFS: Mounted root` *(QEMU)* | root found |
| | `macb e000b000.ethernet … PHY … RTL8211E` *(source)* | Ethernet |
| +20-60 s | `Debian GNU/Linux 13 eclypse-z7 ttyPS0` `eclypse-z7 login:` *(QEMU)* | systemd up. `root` or `dev`, password `zynq7000` |

When it works: `uname -a`, `cat /proc/cpuinfo | grep -c processor` (2), `ip -br a`, `lsblk`, `dmesg`.

## C. What to capture (always, even when it works)

1. **`boot.log`** from power-on to the failure (or to the login), as above.
2. If you reached U-Boot (press a key at `Hit any key`):

   ```text
   Zynq> version
   Zynq> bdinfo
   Zynq> mmc info
   Zynq> part list mmc 0
   Zynq> ls mmc 0:1 /
   Zynq> printenv boot_targets bootcmd bootargs
   Zynq> md.l 0xf8000258 1        # SLCR BOOT_MODE: 0x5 = SD
   Zynq> md.l 0xf8000100 1        # ARM_PLL_CTRL; with ARM_CLK_CTRL 0xf8000120 the CPU clock
   ```

3. If you reached Linux: `dmesg > dmesg.txt`, `cat /proc/cmdline`, `cat /proc/cpuinfo`, `lsmod`, and a photo of the board
   (jumper position, LEDs).
4. The **exact** card image: `sha256sum build/deploy/*.img`, and `./build.sh info`.

## D. Failures, by the first line that identifies them

| What you see (the **first** wrong thing) | Meaning | What to do |
| --- | --- | --- |
| The serial device never appears on the PC | the board is not powered: switch, 12 V, the USB cable is power-only, or the wrong connector | check J11 and the switch; the FTDI needs the board's supply |
| The device appears, **nothing** is printed, not even garbage | the BootROM did not run the SPL: JP5 is not on SD (power-cycled after moving it?), card not seen (not seated, wrong slot, not FAT32 in partition 1), `BOOT.BIN` missing, misnamed or corrupt, or `ps7_init` hung before the UART worked | re-check A; try another card; put JP5 on QSPI to see whether a factory image talks (it proves power, UART and cable); read `BOOT.BIN` back from the card (`cmp`) |
| **Garbage characters** at the start | baud mismatch, or the UART clock is wrong: `ps7_init` was made for a different board | confirm 115200; if so, the PS7 file is not this board's: [03](03-uboot-spl.md) |
| `U-Boot SPL 2026.07…` then **silence** | SPL console fine, stuck in SD init: the card is not responding | another card (some cards are picky at the default speed); reseat |
| `Trying to boot from MMC1` then `Error: -2` (or another negative number) | the SPL read the card but could not find or read `u-boot.img` | `mdir -i /dev/sdX1 ::` shows the file name; rewrite the card |
| `SPL: failed to boot from all boot devices` | the same, after all devices | same |
| `Unsupported boot mode selected` | the boot-mode pins are in a position the SPL does not handle | JP5 on SD, power-cycle |
| The SPL banner **repeats** forever | the SPL crashed or reset after the banner (watchdog, a bad DDR set-up) | compare with a known-good card; suspect the PS7 file; capture `boot.log` |
| `U-Boot 2026.07…` then hangs at `DRAM:` | DDR set-up is wrong: `ps7_init` does not match the memory (or the size in the device tree) | the PS7 file, [03](03-uboot-spl.md) |
| `DRAM:  1 GiB` then hangs at `MMC:` | SD host in U-Boot proper | `mmc info` is not reachable; send the log |
| U-Boot reaches `Hit any key…` and `Scanning mmc 0:1…` but **no** `Found /extlinux/extlinux.conf` | not found at `extlinux/extlinux.conf` on the **active** FAT partition | at the prompt `ls mmc 0:1 /extlinux`; `part list mmc 0` |
| `** Unable to read file /zImage **` | name mismatch | `ls mmc 0:1 /` |
| `Bad Linux ARM zImage magic!` | not a 32-bit zImage | rebuild; `file zImage` says "Linux kernel ARM boot executable zImage" |
| `Starting kernel ...` then **nothing**, not even earlycon lines | the kernel did not start or the console is wrong (device tree not applied, wrong `earlycon`/`console`) | at the U-Boot prompt run the commands of [09](09-troubleshooting.md#u-boot-starts-but-linux-does-not) by hand; try without `earlycon`; check the DTB is `zynq-eclypse-z7.dtb` |
| Kernel lines, then `Waiting for root device PARTUUID=5a796e71-02...` | the root device does not appear: the SD controller did not probe, or the card is not seen from Linux | look for `mmc0:` lines in `dmesg`; compare with the QEMU log; the root is *partition 2* |
| `VFS: Cannot open root device` / `Unable to mount root fs` | partition 2 missing or damaged | re-write; run `fsck` on the ext4 on your PC |
| `Kernel panic … No working init found` / `Attempted to kill init` | not a 32-bit ARM root filesystem, or `/sbin/init` missing | [05](05-rootfs.md) |
| `kernel BUG at drivers/cpufreq/cpufreq.c:1529!` after `cpu cpu0: _opp_config_clk_single: failed to set clock rate` | the CPU clock that `ps7_init` set (666.667 MHz here) is not an operating point the kernel knows (666667 or 333334 kHz), so cpufreq tries to change it and fails. On a board it means the PS7 file is not this board's. In QEMU (no `ps7_init`) it is an artefact | boot once with `cpufreq.off=1` appended to the `APPEND` line to get past it, and report the real frequency (`md.l 0xf8000100 1`) |
| `smp: Brought up 1 node, 1 CPU` on the board | the second core did not start | report; check `dmesg` for `CPU1`. (QEMU also shows one CPU: its U-Boot path does not release core 1) |
| Login works, **no network** | `end0` has no link/DHCP, or the PHY did not attach (`Could not attach PHY (-19)` / `MDIO device at address 1 is missing`) | check the cable and the link LED on J3; capture the `macb`, `phy` and `mdio` lines of `dmesg` |
| `ssh.service` fails | see [09](09-troubleshooting.md): host keys | `journalctl -u ssh` |

## E. What to send back

The `boot.log`, the answers to section C, the line of section D you matched, the image's sha256 and `./build.sh info`.
With those, the failing stage is nearly always visible from the *last good line*.

## F. Once it boots

1. Remove `earlycon` (`KERNEL_CMDLINE_EXTRA="rootwait rw"`, `./build.sh image`, or edit `extlinux/extlinux.conf` on the card).
2. Change the default password; `sudo ./build.sh flash -d /dev/sdX --expand` to use the whole card.
3. Keep this card as the known-good fallback before you start on the PL ([13](13-zmod-adc.md)).

Next: [15 · Acronyms](15-acronyms.md).
