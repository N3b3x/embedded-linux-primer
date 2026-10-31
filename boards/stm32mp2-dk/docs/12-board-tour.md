# 12 · Board tour: the STM32MP257F-DK and what this build uses of it

This chapter is a map of the hardware, **limited to what can be read from the sources pinned by this
repository** (device trees, the TF-A, OP-TEE and U-Boot trees, the kernel). For connector positions, switch
tables and electrical details, the authority is ST's *user manual* and *quick-start guide* for the
STM32MP257F-DK on st.com.

## The chip

The STM32MP257F is a member of ST's STM32MP2 family:

| Part number letter | Meaning (from TF-A's `docs/plat/st/stm32mp2.rst`) |
| --- | --- |
| `STM32MP257` | the top of the STM32MP25 line: **dual Cortex-A35**, one **Cortex-M33**, 3× Ethernet (2 + a switch port), 3× CAN FD, H.264 video, 3D GPU, AI/NN accelerator, LVDS |
| `F` | secure boot + hardware crypto + Cortex-A35 at 1.5 GHz |

Three processing units live in the one chip, in different roles:

| Core | Use on this board here |
| --- | --- |
| 2 × Cortex-A35 (ARMv8.0, 64-bit) | everything in this repository: BL2, BL31, OP-TEE, U-Boot, Linux. Their boot is the subject of [01](01-boot-flow.md) |
| 1 × Cortex-M33 | not used. ST's file names say `ca35tdcid` (in TF-A's `fdts/` and the kernel's and OP-TEE's `…-rcc.dtsi`, `…-rif.dtsi`): the A35 is the "TDCID", the core that sets up the system's compartments, and it may start the M33 later |
| GPU, NPU, video codec | no driver is enabled for them by the mainline device tree of this kit at the pinned kernel (see below) |

## What the kit carries (that the sources mention)

From `arch/arm64/boot/dts/st/stm32mp257f-dk.dts` of the pinned kernel, `fdts/stm32mp257f-dk.dts` of TF-A and
U-Boot's `arch/arm/dts/stm32mp257f-dk-u-boot.dtsi`:

| Hardware | Evidence in the sources |
| --- | --- |
| **4 GiB LPDDR4** | `memory@80000000 { reg = <0x0 0x80000000 0x1 0x0>; }` (kernel); `stm32mp25-lpddr4-1x32Gbits-1x32bits-1200MHz.dtsi` (TF-A DDR description) |
| **microSD slot** | `&sdmmc1`, card-detect on `gpiod 3`, 4-bit bus, supplies from SCMI regulators |
| **Gigabit Ethernet** | `&ethernet1`, RGMII, a Realtek PHY (`ethernet-phy-id001c.c916`) with reset on `gpioa 2`; Linux driver `dwmac-stm32` |
| **Serial console** | `&usart2` (`serial0`, `stdout-path = "serial0:115200n8"`); wired to an on-board ST-LINK that appears as a USB serial port |
| **Heartbeat LED** | `led-blue` on `gpioh 7`, trigger `heartbeat` (default off) |
| **Two user buttons** | `gpio-keys`: `User-1` on `gpioc 5` (`BTN_1`), `User-2` on `gpioc 11` (`BTN_2`) |
| **Watchdog** | `&arm_wdt` (the Arm SMC watchdog, serviced by the secure world), `timeout-sec = <32>` |
| **A power-management IC** | the SD card's supply is `VOLTD_SCMI_STPMIC2_LDO7`: LDO7 of an STPMIC2 chip, controlled by the secure world ([11](11-secure-world-and-scmi.md)) |

The kit has more hardware than this (ST's documentation lists the display, USB, audio, wireless and more).
In the pinned mainline kernel those peripherals are **not enabled** in the DK's device tree, so this first-steps image
gives you: console, SD card, Ethernet, the LED and the buttons. That is what the mainline tree supports at
6.18.58; it is also exactly what is needed to learn the boot chain. Every further peripheral is a device-tree
change plus, perhaps, a kernel option ([08](08-customizing.md)); the secure world's firewall (RIF) must also
allow Linux to use it ([11](11-secure-world-and-scmi.md#two-worlds-one-cpu)).

## What the boot chain reads from the board

* **Boot pins** (switches): choose SD, eMMC, NAND/NOR or the serial/USB download mode. Read from the ROM and
  passed to U-Boot as `boot_device`/`boot_instance` ([03](03-firmware-and-uboot.md)).
* **SDMMC1** for the card; U-Boot's `mmc` numbering is derived from the device tree (`mmc@48220000` for
  SDMMC1, `STM32_SDMMC1_BASE` in `arch/arm/mach-stm32mp/stm32mp2/cpu.c`).
* **USART2** for every stage's text output.

## Connectors you will use

| Purpose | What to look for on the board |
| --- | --- |
| power | the kit's power input: check the voltage and connector in the user manual before connecting a supply |
| serial console | the USB connector that goes to the on-board **ST-LINK** (also the debug/programming port) |
| microSD | the card slot; the card goes in with this image written to it |
| Ethernet | the RJ45 jack of `ethernet1` |
| boot switches | the bank of switches that sets the boot pins; positions are in the user manual |

## The same chip on other boards

Everything in this directory is about the *DK*. A custom board with the same STM32MP257F changes the device
tree (`DTB_FILE_NAME` in TF-A, `CFG_EMBED_DTB_SOURCE_FILE` in OP-TEE, `DEVICE_TREE` in U-Boot, the kernel
DTB), the DDR description (a different memory chip needs a different `.dtsi` and perhaps a different
`STM32MP_*_TYPE`), and the pin set. [08](08-customizing.md) shows where each goes.

Next: [13 · Acronyms](13-acronyms.md).
