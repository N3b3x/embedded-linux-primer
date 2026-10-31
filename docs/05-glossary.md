# 05 · Glossary

The terms that appear in more than one board directory, in plain words. Terms that belong to one
chip family only are in that board's own acronym chapter:
[i.MX 8M Plus](../boards/imx8mp-variscite/docs/14-acronyms.md).

## Hardware

| Term | Meaning |
| --- | --- |
| **SoC** | System on Chip. One chip with CPU cores, memory controller and peripherals. |
| **SoM / module** | System on Module. The SoC, DRAM, flash and power chips on a small board that plugs into a carrier. |
| **Carrier board** | The board a module sits on: connectors, regulators, the debug USB-serial port. |
| **Devkit / DK** | A SoM or SoC on a carrier sold for development, with a debug UART and boot-mode switches. |
| **Boot ROM** | Immutable code inside the SoC that runs first and loads the first stage. |
| **OCRAM / SRAM** | On-chip RAM. The only memory that works before DRAM is trained. |
| **DRAM, DDR, LPDDR4** | The main memory. DDR4/LPDDR4 interfaces must be *trained* at every power-up. |
| **PHY** | The analogue interface block of a memory or network controller. |
| **PMIC** | Power Management IC. Sequences and regulates the supplies; configured over I²C. |
| **eMMC** | Soldered flash with an SD-like interface. The usual production storage. |
| **QSPI / NOR flash** | Small serial flash chip, usually holding boot firmware only. |
| **NVMe** | PCIe solid-state drive. Used as the root filesystem on larger boards. |
| **UART** | Serial port. The debug console of every board here, at 115200 baud, 8N1. |
| **I²C, SPI, GPIO** | The simple buses and pins that sensors and small peripherals use. |
| **Pinmux** | Which function (UART, SPI, GPIO…) each physical pin of the SoC currently has. |
| **Boot-mode switch / pins** | Hardware inputs that tell the Boot ROM where to look for the first stage. |

## Boot software

| Term | Meaning |
| --- | --- |
| **First-stage loader** | The first code the Boot ROM loads; initialises DRAM and loads the rest. SPL (U-Boot), BL2 (TF-A), MB1/MB2 (NVIDIA). |
| **SPL** | Secondary Program Loader. A tiny build of U-Boot that fits in on-chip RAM. |
| **TF-A** | Trusted Firmware-A. The reference secure monitor for 64-bit Arm; stages named BL1, BL2, BL31, BL32, BL33. |
| **BL2 / BL31 / BL32 / BL33** | TF-A boot stages: BL2 loads the others; BL31 is the resident secure monitor (EL3); BL32 is the trusted OS (OP-TEE); BL33 is the normal-world bootloader (U-Boot). |
| **FIP** | Firmware Image Package. A container file holding BL31, BL32, BL33 and their device trees; built with `fiptool`. |
| **OP-TEE** | Open Portable Trusted Execution Environment. A small trusted OS that runs in the secure world. |
| **TEE, TrustZone** | Trusted Execution Environment; the Arm hardware feature that splits the system into a secure and a normal world. |
| **EL0–EL3** | Arm exception (privilege) levels: EL0 applications, EL1 kernel, EL2 hypervisor, EL3 secure monitor. |
| **SMC** | Secure Monitor Call. The instruction that enters EL3 from a lower level. |
| **PSCI** | Power State Coordination Interface. The SMC API Linux uses to start, stop and suspend CPUs. |
| **SCMI** | System Control and Management Interface. A standard way for the kernel to ask a firmware agent to set clocks, resets and voltages. |
| **U-Boot** | The most common embedded bootloader. Has a prompt, filesystem drivers and an environment. |
| **UEFI** | Unified Extensible Firmware Interface. The bootloader standard used on Jetson and on PCs. |
| **Environment** | U-Boot's named variables (`bootcmd`, `bootargs`, `fdt_file`…), stored in flash or read from a file. |
| **extlinux.conf** | A small text file U-Boot's distro boot reads to learn which kernel, device tree and arguments to use. |
| **Kernel command line** | The string of `key=value` arguments the bootloader hands the kernel (`console=`, `root=`). |
| **Recovery mode** | A Boot ROM state in which the chip waits for a host over USB to send it code. How Jetson is flashed. |

## Kernel and filesystem

| Term | Meaning |
| --- | --- |
| **DT, DTS, DTB** | Device tree, its source (`.dts`/`.dtsi`) and its compiled binary (`.dtb`). |
| **Device tree overlay** | A small `.dtbo` that patches the base tree at boot (enable a node, add a sensor). |
| **Kconfig, defconfig** | The kernel's build options; a defconfig is a saved minimal set. A *fragment* adds to one. |
| **Module (`.ko`)** | A driver loaded after boot instead of built into the kernel. |
| **initramfs** | A small filesystem the kernel unpacks into RAM first; used to find or unlock the real root. |
| **rootfs** | The root filesystem, mounted at `/`. |
| **init, systemd, BusyBox** | PID 1: the first program in user space; systemd is the full one, BusyBox's init the tiny one. |
| **mmdebstrap, debootstrap** | Tools that build a Debian root filesystem from the package archive. |
| **GPT, MBR** | Partition table formats. The STM32MP2 ROM needs GPT with named partitions; i.MX 8M Plus uses a plain MBR table. |
| **PARTUUID** | The unique ID stored in a GPT (or MBR) partition entry. `root=PARTUUID=…` finds a root without caring about device numbering. |
| **ext4** | The default Linux filesystem for root partitions here. |
| **bmap** | A map of the used blocks of an image; lets `bmaptool` write only those, much faster than `dd`. |

## Build

| Term | Meaning |
| --- | --- |
| **Cross-compiler** | A compiler that runs on your PC but produces code for another CPU (`aarch64-none-linux-gnu-gcc`). |
| **Bare-metal toolchain** (`aarch64-none-elf-`) | A cross-compiler with no operating-system target; used for firmware that runs before Linux. |
| **Pinned** | A source or download fixed to an exact commit or checksum so the build is reproducible. |
| **Explain mode** | `--dry-run`: print every command with a sentence on why, run nothing. |
| **BSP** | Board Support Package. The vendor's bundle of firmware, bootloader, kernel and drivers for a board. |
| **Yocto / OpenEmbedded** | A build system that produces a whole Linux distribution from recipes. Most vendor BSPs are Yocto layers. |
| **EULA** | End-user licence agreement. Some vendor firmware blobs (NXP DDR firmware, NVIDIA's BSP) require accepting one. |
