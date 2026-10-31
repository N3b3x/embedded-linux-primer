# 13 · Acronyms and words

Sorted by what you meet them in. If a word is missing, search the repository: most are explained where they
are first used.

## Boot chain

| Term | Meaning |
| --- | --- |
| **ROM** (Boot ROM) | the code burned into the chip; the first thing that runs; cannot be changed |
| **BL1 / BL2 / BL32 / BL33** | TF-A's "boot loader" stage numbers. **BL2**: loads the others. **BL32**: the trusted OS (OP-TEE). **BL33**: the normal-world bootloader (U-Boot). There is no BL1 on this SoC (the ROM plays that part) and no **BL31** (the 64-bit resident monitor): OP-TEE is the monitor |
| **FSBL** | *first-stage boot loader*; here BL2, in the partitions `fsbl1` / `fsbl2` (the 64-bit board calls them `fsbla1` / `fsbla2`) |
| **TF-A** | *Trusted Firmware-A*: Arm's reference firmware for Cortex-A, hosted at trustedfirmware.org |
| **SP_min** | TF-A's own minimal 32-bit secure monitor; the alternative to OP-TEE that its docs do not recommend |
| **FIP** | *Firmware Image Package*: TF-A's container with a table of contents of images |
| **UUID / GUID** | a 128-bit identifier. The FIP's table uses UUIDs; GPT partitions have a *type GUID* and a unique one |
| **OP-TEE** | *Open Portable Trusted Execution Environment*: the trusted OS that runs in the secure world |
| **pager** | OP-TEE mode in which most of its code lives in DDR and is copied into on-chip SRAM on demand (`tee-pageable_v2.bin`) |
| **TA / PTA** | *trusted application* (runs under OP-TEE) / *pseudo* trusted application (built into OP-TEE's core: PTA-SCMI) |
| **TEE** | *Trusted Execution Environment* |
| **SMC** | *secure monitor call*: the instruction that goes from the non-secure world into the monitor |
| **PSCI** | *Power State Coordination Interface*: how an OS turns CPUs on and off through firmware |
| **U-Boot** | *Das U-Boot*, the universal bootloader |
| **SPL** | *secondary program loader*: U-Boot's small first stage on other SoCs; not used here (BL2 does that job) |
| **distro boot** | U-Boot's generic way of finding an operating system on a disk (`bootcmd`, `distro_bootcmd`) |
| **extlinux.conf** | a small text file that tells the bootloader which kernel, device tree and command line to use (originally from syslinux) |
| **sysboot** | U-Boot command that reads `extlinux.conf` |
| **bootz** | U-Boot command that starts a 32-bit ARM `zImage` |

## CPU and privilege

| Term | Meaning |
| --- | --- |
| **Armv7-A / AArch32** | the 32-bit ARM architecture and execution state. The Cortex-A7 is Armv7-A |
| **processor mode** | User, Supervisor (SVC), Monitor, Hypervisor (HYP) ...: the 32-bit counterpart of exception levels |
| **secure / normal world** | the two security states of the CPU (Arm *TrustZone*). Hardware firewalls use it |
| **armhf / armv7** | the Debian / Alpine names for 32-bit ARMv7 with hardware floating point |
| **zImage** | a self-decompressing 32-bit ARM kernel |
| **GIC** | *Generic Interrupt Controller* |
| **MMU** | memory management unit |

## Memory and storage

| Term | Meaning |
| --- | --- |
| **SYSRAM** | on-chip static RAM (256 KiB at `0x2FFC0000`). Works before the DDR does |
| **DDR3** | the external memory (here 512 MiB). Its controller is set up by BL2 |
| **GPT / MBR** | the two partition-table formats: *GUID Partition Table* (used here) and the old DOS *master boot record* |
| **PARTUUID** | the unique GUID of a GPT partition, usable on the kernel command line (`root=PARTUUID=…`) |
| **PARTLABEL / label** | a partition's name (GPT) / a filesystem's name (ext4) |
| **ext4** | the Linux root filesystem used here |
| **SD / SDMMC** | the card format / the controller block (SDMMC1 is the microSD slot) |
| **bmap** | a file listing the blocks of an image that hold data, so `bmaptool` can skip the rest |

## Firewalls, power and clocks

| Term | Meaning |
| --- | --- |
| **ETZPC** | *Extended TrustZone Protection Controller*: sets, per peripheral, whether the secure world, the normal world or both may use it |
| **TZC-400** | Arm's TrustZone Address Space Controller: the DDR firewall |
| **TZEN** | the bit in the RCC (`RCC_TZCR`) that, once set by OP-TEE, makes the clock/reset controller secure |
| **RCC** | *Reset and Clock Controller*: the peripheral that holds the clock tree and resets |
| **PMIC / STPMIC1** | the power-management chip on I²C4 and its ST part number |
| **HSE / HSI / CSI / LSE / LSI** | high/low-speed external/internal oscillators: the clock roots |
| **SCMI** | *System Control and Management Interface*: Arm's message protocol for clocks, resets, voltages, … between an OS (agent) and a platform |
| **voltage domain** | the SCMI name for a regulator (protocol `0x17`) |
| **RIF** | the 64-bit STM32MP2's newer firewall scheme; not on this chip |

## Linux and the build

| Term | Meaning |
| --- | --- |
| **DT / DTS / DTB / DTC** | *device tree* and its source / binary / compiler. Describes the hardware to the kernel |
| **dtsi** | an include file for a device tree |
| **`compatible`** | the string in a device-tree node that a driver matches |
| **probe** | the moment a driver binds to a device |
| **initramfs** | a root filesystem unpacked into RAM at boot; not used here |
| **defconfig / fragment** | a saved kernel configuration / a few lines merged on top of it |
| **multi_v7_defconfig** | the shared 32-bit ARMv7 kernel configuration |
| **LOCALVERSION** | the suffix of `uname -r` |
| **BSP** | *board support package*: the firmware, kernel and configuration for one board |
| **mmdebstrap / fakeroot** | tools that build a root filesystem / make files look root-owned without root |
| **qemu-user / binfmt_misc** | the emulator that runs 32-bit ARM programs on a PC / the kernel feature that starts it automatically |
| **UART / USART / VCP** | serial port / its synchronous-capable ST variant (`ttySTM0` is UART4) / a *virtual COM port* made by the ST-LINK |
| **ST-LINK** | ST's on-board debug probe; also bridges the serial console to USB |
| **STM32CubeProgrammer** | ST's tool for loading firmware over USB or UART (recovery) |

Back to the start: [README](../README.md) · [docs index](README.md).
