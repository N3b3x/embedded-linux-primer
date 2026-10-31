# STM32MP257F-DK · documentation

Read in order the first time; afterwards each chapter stands alone.

| # | Chapter | Answers |
| --- | --- | --- |
| 01 | [Boot flow](01-boot-flow.md) | What runs from power-on to a login prompt, at which privilege level, loaded by whom? |
| 02 | [Host setup](02-host-setup.md) | What do I need on my PC, and what does a build cost? |
| 03 | [Firmware and U-Boot](03-firmware-and-uboot.md) | How are BL2, BL31, OP-TEE, U-Boot and the FIP built, and what is inside? |
| 04 | [The kernel](04-kernel.md) | Which kernel, which configuration, which device tree, how long? |
| 05 | [The root filesystem](05-rootfs.md) | Debian, Alpine, or my own: what is in `/`? |
| 06 | [The SD card image](06-sdcard-image.md) | Byte for byte, what is on the card? |
| 07 | [Flashing and booting](07-flashing-and-booting.md) | Write the card, set the board up, what to look for on the console |
| 08 | [Customizing](08-customizing.md) | Where does each kind of change go? |
| 09 | [Troubleshooting](09-troubleshooting.md) | The failures, by the last thing you saw |
| 10 | [Versions](10-versions.md) | What is pinned, why, how to move |
| 11 | [Secure world and SCMI](11-secure-world-and-scmi.md) | Why does Linux ask OP-TEE for a clock? |
| 12 | [Board tour](12-board-tour.md) | What is on the kit, what this build uses |
| 13 | [Acronyms](13-acronyms.md) | Every three-letter word |
| 14 | [First-boot checklist](14-first-boot-checklist.md) | Which switches, which log line proves which stage, what to send back when it is silent |
| 15 | [The two stacks](15-two-stacks.md) | Mainline or ST's own set: versions, device trees, SCMI, FWU metadata, SD layout |

Diagrams are in [`images/`](images/README.md).
