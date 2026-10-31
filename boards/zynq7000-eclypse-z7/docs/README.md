# Digilent Eclypse Z7 · documentation

Read in order the first time; afterwards each chapter stands alone.

| # | Chapter | Answers |
| --- | --- | --- |
| 01 | [Boot flow](01-boot-flow.md) | What runs from power-on to a login prompt, in which mode, loaded by whom? |
| 02 | [Host setup](02-host-setup.md) | What do I need on my PC, and what does a build cost? |
| 03 | [The first stage and the bootloader](03-uboot-spl.md) | How are `BOOT.BIN` and `u-boot.img` built, what is in them, where does `ps7_init` come from? |
| 04 | [The kernel](04-kernel.md) | Which kernel, which configuration, which device tree? |
| 05 | [The root filesystem](05-rootfs.md) | Debian armhf, Alpine armv7 or my own: what is in `/`? |
| 06 | [The SD card image](06-sdcard-image.md) | Byte for byte, what is on the card, and why MBR? |
| 07 | [Flashing and booting](07-flashing-and-booting.md) | Write the card, set JP5, open the serial port, what to look for |
| 08 | [Customizing](08-customizing.md) | Where does each kind of change go? |
| 09 | [Troubleshooting](09-troubleshooting.md) | The failures, by the last thing you saw |
| 10 | [Versions](10-versions.md) | What is pinned, why, how to move |
| 11 | [PS and PL](11-ps-and-pl.md) | What is the processing system and the programmable logic, and how does this SoC differ from the other boards? |
| 12 | [Board tour](12-board-tour.md) | What is on the Eclypse Z7, what this build uses |
| 13 | [Where the Zmod ADC fits](13-zmod-adc.md) | What a Zmod needs before it works: a map, not a build |
| 14 | [First-boot checklist](14-first-boot-checklist.md) | The day you power it: what to see, what to capture, failures by first log line |
| 15 | [Acronyms](15-acronyms.md) | Every three-letter word |

Diagrams are in [`images/`](images/README.md).
