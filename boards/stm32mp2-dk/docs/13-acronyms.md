# 13 · Acronyms and words

Sorted by what you meet them in. If a word is missing, search the repository: most are explained where they
are first used.

## Boot chain

| Term | Meaning |
| --- | --- |
| **ROM** (Boot ROM) | the code burned into the chip; the first thing that runs; cannot be changed |
| **BL1 / BL2 / BL31 / BL32 / BL33** | TF-A's "boot loader" stage numbers. **BL2**: loads the others. **BL31**: the resident secure monitor. **BL32**: the trusted OS (OP-TEE). **BL33**: the normal-world bootloader (U-Boot). There is no BL1 on this SoC: the ROM plays that part |
| **FSBL** | *first-stage boot loader*; here BL2, in the partitions `fsbla1` / `fsbla2` ("a" for the Cortex-A; TF-A's platform makefile also mentions `fsbl-m` partitions for the Cortex-M33) |
| **TF-A** | *Trusted Firmware-A*: Arm's reference firmware for ARMv8-A, hosted at trustedfirmware.org |
| **FIP** | *Firmware Image Package*: TF-A's container with a table of contents of images |
| **UUID / GUID** | a 128-bit identifier. The FIP's table uses UUIDs; GPT partitions have a *type GUID* and a unique one |
| **OP-TEE** | *Open Portable Trusted Execution Environment*: the trusted OS that runs in the secure world |
| **TA / PTA** | *trusted application* (runs under OP-TEE) / *pseudo* trusted application (built into OP-TEE's core: PTA-SCMI) |
| **TEE** | *Trusted Execution Environment* |
| **SPD** | *secure payload dispatcher*: the BL31 module that forwards `smc` calls to a trusted OS (`SPD=opteed`) |
| **SMC** | *secure monitor call*: the instruction that goes from EL1/EL2 to EL3 |
| **PSCI** | *Power State Coordination Interface*: how an OS turns CPUs on and off through firmware |
| **U-Boot** | *Das U-Boot*, the universal bootloader |
| **SPL** | *secondary program loader*: U-Boot's small first stage on other SoCs; not used here (BL2 does that job) |
| **distro boot** | U-Boot's generic way of finding an operating system on a disk (`bootcmd`, `distro_bootcmd`) |
| **extlinux.conf** | a small text file that tells the bootloader which kernel, device tree and command line to use (originally from syslinux) |
| **sysboot** | U-Boot command that reads `extlinux.conf` |
| **booti** | U-Boot command that starts an arm64 `Image` |

## CPU and privilege

| Term | Meaning |
| --- | --- |
| **ARMv8-A / AArch64** | the 64-bit ARM architecture and its 64-bit execution state. The Cortex-A35 is ARMv8.0-A |
| **EL0 – EL3** | *exception levels*: privilege levels. EL3 is the most privileged |
| **S-EL1 / NS-EL1** | EL1 in the secure / non-secure state |
| **secure / normal world** | the two security states of the CPU (Arm *TrustZone*). Hardware firewalls use it |
| **ERET** | *exception return*: how a more privileged level hands control to a lower one |
| **GIC** | *Generic Interrupt Controller* |
| **MMU** | memory management unit |

## Memory and storage

| Term | Meaning |
| --- | --- |
| **SYSRAM / SRAM1** | on-chip static RAM (256 KiB at `0x0E000000` and the block above it). Works before the DDR does |
| **DDR / LPDDR4** | the external memory (here 4 GiB of low-power DDR4). Needs *training* at every power-up |
| **PHY / PMU** | the physical interface block of the DDR controller / the small processor inside it that runs the training code |
| **GPT / MBR** | the two partition-table formats: *GUID Partition Table* (used here) and the old DOS *master boot record* |
| **PARTUUID** | the unique GUID of a GPT partition, usable on the kernel command line (`root=PARTUUID=…`) |
| **PARTLABEL / label** | a partition's name (GPT) / a filesystem's name (ext4) |
| **ext4** | the Linux root filesystem used here |
| **SD / SDMMC / eMMC** | the card format / the controller block (SDMMC1 is the microSD slot) / on-board flash that looks like a card |
| **bmap** | a file listing the blocks of an image that hold data, so `bmaptool` can skip the rest |

## Firewalls and clocks

| Term | Meaning |
| --- | --- |
| **RIF / RIFSC / RISAB / RISAF** | *Resource Isolation Framework*: ST's per-peripheral (RIFSC), SRAM (RISAB) and memory (RISAF) access control |
| **RCC** | *Reset and Clock Controller*: the peripheral that holds the clock tree and resets |
| **HSE / HSI / MSI / LSE / LSI** | high/medium/low-speed external/internal oscillators: the clock roots |
| **ICN** | *interconnect*: the bus clocks (`ICN_SDMMC`, …) |
| **FLEXGEN** | ST's flexible clock-generator outputs that feed the peripherals' kernel clocks |
| **SCMI** | *System Control and Management Interface*: Arm's message protocol for clocks, resets, voltages, … between an OS (agent) and a platform |
| **SCP / SCP-firmware** | *System Control Processor*; Arm's firmware framework for one, whose SCMI stack OP-TEE embeds |
| **SMT** | *shared memory transport*: how SCMI messages sit in a buffer both sides can see |

## Linux and the build

| Term | Meaning |
| --- | --- |
| **DT / DTS / DTB / DTC** | *device tree* and its source / binary / compiler. Describes the hardware to the kernel |
| **dtsi** | an include file for a device tree |
| **`compatible`** | the string in a device-tree node that a driver matches |
| **probe** | the moment a driver binds to a device |
| **initramfs** | a root filesystem unpacked into RAM at boot; not used here |
| **defconfig / fragment** | a saved kernel configuration / a few lines merged on top of it |
| **LOCALVERSION** | the suffix of `uname -r` |
| **BSP** | *board support package*: the firmware, kernel and configuration for one board |
| **mmdebstrap / fakeroot** | tools that build a root filesystem / make files look root-owned without root |
| **UART / USART / VCP** | serial port / its synchronous-capable ST variant (`ttySTM0` is USART2) / a *virtual COM port* made by the ST-LINK |
| **ST-LINK** | ST's on-board debug probe; also bridges the serial console to USB |
| **STM32CubeProgrammer** | ST's tool for loading firmware over USB or UART (recovery) |
| **TDCID** | ST's term for the core that sets up the system's compartments (the A35 here) |
| **OSTL** | *OpenSTLinux*: ST's Yocto-based distribution; `-ostl` in a device-tree name marks ST's tree for it |
| **PSA FWU / FWU metadata** | Arm's *firmware update* scheme: a small record that names two banks of firmware and which is active. TF-A's `PSA_FWU_SUPPORT=1` makes BL2 read it; `mkfwumdata` writes it |
| **dt-stm32mp** | ST's repository of device trees for TF-A, OP-TEE, U-Boot and Linux (`STACK=st`) |

Back to the start: [README](../README.md) · [docs index](README.md).
