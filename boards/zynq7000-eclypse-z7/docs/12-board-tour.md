# 12 · Board tour: the Eclypse Z7 and what this build uses

The Digilent **Eclypse Z7** is a prototyping platform around an AMD/Xilinx **Zynq-7000 XC7Z020-1CLG484C**, built
to host *Zmod* and other SYZYGY modules. The facts below come from Digilent's *Eclypse Z7 Reference Manual*
(Digilent's online manual; section numbers refer to it) and from the Vivado board preset for it.

## What is on the board

| Block | Part / detail | Connected to | Used by this build |
| --- | --- | --- | --- |
| SoC | XC7Z020-1CLG484C: 2 × Cortex-A9 up to 667 MHz + Artix-7-class fabric | | yes (the PS) |
| Memory | 2 × ISSI IS43TR16256A DDR3L, 32-bit bus, **1 GiB**, 1066 MT/s | PS DDR controller | yes: configured by `ps7_init` |
| Flash | 16 MB Quad-SPI, factory MAC (EUI-48) in its OTP area | PS QSPI, MIO 1-6, 8 | described in the device tree; **not** used for boot |
| microSD | slot **J4**, "SD CARD", card detect | PS SD0, MIO 40-45, 47 | **yes: the boot and root medium** |
| Boot mode | jumper **JP5**: `JTAG` / `QSPI` / `SD` | the Zynq's mode pins | set it to **SD** |
| USB-UART | FTDI FT2232HQ on micro-USB **J6** (also the JTAG interface) | PS UART0, MIO 14/15 | **yes: the console, 115200 8N1** |
| Ethernet | RTL8211E-VL PHY, RJ45 **J3**, RGMII, MDIO address 1 | PS GEM0, MIO 16-27, MDIO 52/53, reset MIO 9 | yes (Linux) |
| USB | micro-AB OTG port with a ULPI PHY, reset MIO 46 | PS USB0, MIO 28-39 | host mode in the device tree |
| I2C | the platform MCU (ATmega328PB) at I2C address `0x60`: SYZYGY SmartVIO supplies, die temperature, fan | PS I2C, MIO 12/13 | node enabled; no driver in this build |
| Zmod ports | **two SYZYGY ports**, A and B; each has its own PL I/O bank, a variable supply (VADJ), differential clocks | **PL pins only** | no: [13](13-zmod-adc.md) |
| Pmod ports | two 12-pin Pmods | PL pins | no |
| Buttons, LEDs | 2 push-buttons, 2 tri-colour LEDs | PL pins | no (they exist only once a design drives them) |
| PS reset | BTNR (underside): resets the Zynq; does **not** re-read JP5 | | |
| Power | 12 V 5 A barrel jack **J11**, power switch; rails sequenced by a custom sequencer | | |
| PL clock | 125 MHz, from the Ethernet PHY's reference output, to pin D18 | PL | no |
| JTAG | USB-JTAG on J6 and an external JTAG header (JP3 selects independent JTAG) | | recovery only |

## What the build turns on

The device tree `custom/dts/zynq-eclypse-z7.dts` enables: `uart0` (console), `sdhci0` (the card), `gem0` with its
PHY (network), `gpio0` (PHY and USB resets), `i2c1`, `qspi` with a flash node, `usb0` (host), and leaves the
programmable-logic nodes from `zynq-7000.dtsi` (`devcfg`, `fpga-region`) alone. Not enabled, because they are
not on the processing system's pins: the buttons, LEDs and Pmods. Their drivers appear when a PL design wires them.

## What you will see on a PS-only boot

| Observation | Why |
| --- | --- |
| the UART LEDs (LD4) blink during the boot | traffic on the FT2232HQ |
| the Ethernet LEDs on J3 light when a cable is connected | PHY link; `end0` appears in Linux |
| no LEDs of your own | they belong to the PL |
| `/sys/class/fpga_manager/fpga0` after `modprobe zynq-fpga` reports `unknown` | the fabric has no configuration |
| a variable-voltage rail (VADJ LEDs LD2, LD3) lit only if a pod is plugged in | the platform MCU powers a port when it finds a pod |

## Names you will meet

* **Vivado board files** for this board: `eclypse-z7` in Digilent's `vivado-boards` repository. The board
  preset in them defines the PS configuration that `ps7_init_gpl.c` encodes.
* **`Eclypse-Z7-OS`**, **`Eclypse-Z7-HW`**: Digilent's PetaLinux and hardware projects. This build takes one file
  from the first (the PS7 initialisation) and nothing else.
* **Zmod**: Digilent's name for its SYZYGY pods (Zmod Scope, Zmod AWG, Zmod Digitizer, Zmod SDR).

Next: [13 · Where the Zmod ADC fits](13-zmod-adc.md).
