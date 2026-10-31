# 15 · Acronyms and words

| Word | Meaning |
| --- | --- |
| **ACP** | Accelerator Coherency Port: a PL master port into the Cortex-A9's L2 cache |
| **ADC** | analog-to-digital converter (here the AD9648 on a Zmod Scope) |
| **APU** | Application Processing Unit: the two Cortex-A9 cores, their caches and the SCU |
| **armhf** | Debian's name for 32-bit ARMv7 with hard-float; Alpine calls it `armv7` |
| **AXI** | Arm's on-chip bus: AXI-Lite for registers, AXI-Stream for samples, AXI memory-mapped for DMA |
| **bitstream** | the configuration file of an FPGA; for the PL, a `.bit` (Vivado) or a byte-swapped `.bin` |
| **BIF** | boot image format: the text file that tells `bootgen` which partitions go in `BOOT.BIN` |
| **bootgen** | Xilinx's tool that assembles `BOOT.BIN` (vendor route, chapter 03 appendix) |
| **BOOT.BIN** | the file the BootROM loads: a boot header and the first-stage program (here the U-Boot SPL) |
| **BootROM** | code in mask ROM in the chip that starts the whole boot chain |
| **DCI** | digitally controlled impedance: DDR I/O calibration the PS7 init waits for |
| **devcfg** | the PS's device-configuration interface: how software loads a bitstream into the PL |
| **DTB / DTS / DTSI / DTSO** | device-tree blob / source / include / overlay source |
| **EMIO** | extended MIO: PS peripheral signals routed out through the PL's pins |
| **FIT** | flattened image tree: U-Boot's multi-image container; `u-boot.img` is one |
| **FPGA manager** | the kernel framework (`/sys/class/fpga_manager`) that programs an FPGA |
| **FSBL** | First Stage Boot Loader: Xilinx's first-stage program, replaced here by U-Boot's SPL |
| **GEM** | Gigabit Ethernet MAC (Cadence IP; Linux driver `macb`) |
| **GIC** | generic interrupt controller; `SPI` = shared peripheral interrupt |
| **HDF / XSA** | Xilinx hardware handoff archives (Vivado ≤ 2019.1 / newer); they hold `ps7_init` and the design's address map |
| **HP port** | high-performance AXI slave port: lets PL masters write into DDR |
| **IIO** | the kernel's Industrial I/O subsystem, the usual home of ADC drivers |
| **IRQ_F2P** | the 16 interrupt lines from the PL to the PS |
| **MBR** | master boot record: the classic ("DOS") partition table, the only one the Zynq BootROM reads |
| **MIO** | multiplexed I/O: the 54 pins the PS peripherals use directly |
| **OCM** | on-chip memory: 256 KiB of SRAM, where `BOOT.BIN`'s payload runs |
| **OPP** | operating performance point: a (frequency, voltage) pair used by cpufreq |
| **PARTUUID** | partition identifier; for MBR it is `<disk signature>-<partition number>` |
| **Pmod** | Digilent's 12-pin peripheral-module connector |
| **PMCU** | the platform microcontroller on the Eclypse Z7 (SYZYGY supplies, temperature) |
| **PL** | programmable logic: the FPGA half of the Zynq |
| **PS** | processing system: the hard processor half of the Zynq |
| **PS7 init (`ps7_init`)** | the generated register writes that set up MIO, PLLs, clocks and DDR |
| **SCU / SLCR** | snoop control unit / system-level control registers |
| **SPL** | secondary program loader: the small U-Boot that runs from OCM |
| **SYZYGY** | the open standard for FPGA pods (Opal Kelly); Zmod ports follow it |
| **UG585** | Xilinx's *Zynq-7000 SoC Technical Reference Manual* |
| **UIO** | the kernel's user-space I/O framework |
| **VADJ** | the adjustable I/O supply of a SYZYGY port |
| **Vivado / Vitis** | Xilinx/AMD's FPGA design tool and its embedded-software tool |
| **zImage** | a self-extracting compressed 32-bit ARM kernel |
| **Zmod** | Digilent's SYZYGY pods (Scope, AWG, Digitizer, SDR) |
| **zynqimage** | the `mkimage` image type that writes the Zynq boot header |
