# 12 · Board tour: the STM32MP157F-DK2 and what this build uses of it

This chapter is a map of the hardware, **limited to what can be read from the sources pinned by this
repository** (device trees, the TF-A, OP-TEE and U-Boot trees, the kernel). For connector positions, switch
tables and electrical details, the authority is ST's *user manual* and *quick-start guide* for the
STM32MP157x-DK1/DK2 Discovery Kits on st.com.

## The chip

The STM32MP157F is a member of ST's STM32MP15 family:

| Part | Meaning (from TF-A's `docs/plat/st/stm32mp1.rst`) |
| --- | --- |
| `STM32MP157` | the top of the STM32MP15 line: **dual Cortex-A7**, one **Cortex-M4** at 209 MHz, a 3D GPU, a DSI display interface and CAN FD |
| `F` | secure boot + hardware crypto + Cortex-A7 at 800 MHz |

Two processing units live in the one chip, in different roles:

| Core | Use on this board here |
| --- | --- |
| 2 × Cortex-A7 (Armv7-A, 32-bit) | everything in this repository: BL2, OP-TEE, U-Boot, Linux. Their boot is the subject of [01](01-boot-flow.md) |
| 1 × Cortex-M4 | not used. The kernel's tree has an `m4_rproc` node (remote-processor control, with the reset taken over SCMI), but no firmware is built or loaded here |
| GPU | no driver is enabled for it by the mainline device tree of this kit at the pinned kernel |

## What the kit carries (that the sources mention)

From `arch/arm/boot/dts/st/stm32mp157f-dk2.dts` and `stm32mp15xx-dkx.dtsi` of the pinned kernel, TF-A's
`fdts/stm32mp157c-dk2.dts` and U-Boot's `arch/arm/dts/stm32mp157a-dk1-scmi-u-boot.dtsi`:

| Hardware | Evidence in the sources |
| --- | --- |
| **512 MiB DDR3** | `memory@c0000000 { reg = <0xc0000000 0x20000000>; }` (kernel); `#define DDR_SIZE 0x20000000` in TF-A's `stm32mp157f-dk2-fw-config.dts`; `stm32mp15-ddr3-1x4Gb-1066-binG.dtsi` (one 4 Gbit chip) |
| **microSD slot, the only boot medium** | `&sdmmc1`, card-detect on `gpiob 7`, 4-bit bus, supply `scmi_v3v3`. The board has **no eMMC** (a bench-proven configuration states this for the DK2 and boots microSD only) |
| **Gigabit Ethernet** | `&ethernet0`, RGMII (`phy-mode = "rgmii-id"`), PHY at MDIO address 0; Linux driver `dwmac-stm32` |
| **Serial console** | `&uart4` (`serial0`, `stdout-path = "serial0:115200n8"`); wired to an on-board ST-LINK that appears as a USB serial port (U-Boot's `stm32mp15_st_common.h`: "uart with on-board st-link") |
| **Heartbeat LED** | `led-blue` on `gpiod 11`, trigger `heartbeat` (default off) |
| **Two user buttons** | `User-1` on `gpioa 14` and `User-2` on `gpioa 13`, in U-Boot's tree (`BTN_1`, `BTN_2`) |
| **4" DSI display, touch panel** | `&dsi` with an `orisetech,otm8009a` panel, `&ltdc`, a `focaltech,ft6236` touch controller on I²C1 |
| **Wi-Fi and Bluetooth** | `&sdmmc2` (Broadcom FullMAC, `brcm,bcm4329-fmac`) and `&usart2` (`brcm,bcm43438-bt`) |
| **Audio, HDMI** | `cs42l51` codec and an HDMI transmitter on I²C1, in `stm32mp15xx-dkx.dtsi` |
| **A power-management IC** | an STPMIC1 on I²C4, controlled by the secure world: Linux's I²C4 is `disabled` ([11](11-secure-world-and-scmi.md)) |

This first-steps image gives you **console, SD card, Ethernet, the LED**; the display and touch drivers are
built as modules by `multi_v7_defconfig` and will probe when `udev` loads them on Debian (on Alpine,
`coldplug` does), and Wi-Fi needs a firmware file for the Broadcom chip that this repository does not
download. Treat everything beyond the console and the SD card as "should work, not checked".
Every further peripheral is a device-tree change plus perhaps a kernel option ([08](08-customizing.md)); the
secure world's firewall (ETZPC) must also allow Linux to use it ([11](11-secure-world-and-scmi.md#two-worlds-one-cpu)).

## What the boot chain reads from the board

* **Boot pins** (two switches on the DK2): choose SD, the serial/USB download mode, and so on. Read by the
  ROM and passed on to U-Boot as `boot_device`/`boot_instance` ([03](03-firmware-and-uboot.md)).
* **SDMMC1** for the card.
* **UART4** for every stage's text output.

## Connectors you will use

| Purpose | What to look for on the board |
| --- | --- |
| power | the kit's power input: check the voltage and connector in the user manual before connecting a supply |
| serial console | the USB connector that goes to the on-board **ST-LINK** (also the debug/programming port) |
| microSD | the card slot; the card goes in with this image written to it |
| Ethernet | the RJ45 jack |
| boot switches | the switch that sets the boot pins; positions are in [07](07-flashing-and-booting.md#2-set-the-board-to-boot-from-the-sd-card) |

## The same chip on other boards

Everything in this directory is about the *DK2*. A custom board with the same STM32MP157 changes the device
trees (`DTB_FILE_NAME` in TF-A, `CFG_EMBED_DTB_SOURCE_FILE` in OP-TEE, `DEVICE_TREE` in U-Boot, the kernel
DTB), the DDR description (a different memory chip needs a different `.dtsi`), and the pin set.
[08](08-customizing.md) shows where each goes. The STM32MP13 (single Cortex-A7, the DK `stm32mp135f-dk`) uses
the same platform code with `STM32MP13=1`; it is not covered here.

Next: [13 · Acronyms](13-acronyms.md).
