# 04 · Choosing a board

Five boards, five different lessons. Start with the one whose lesson you need, not the one with
the most impressive hardware.

## At a glance

| Board | Directory | How software gets on | Sources | What you build | Verified so far |
| --- | --- | --- | --- | --- | --- |
| **i.MX 8M Plus** (Variscite) | [`imx8mp-variscite`](../boards/imx8mp-variscite/README.md) | SD-card image, or USB with `uuu` into the eMMC | Variscite's forks of NXP's U-Boot, TF-A and Linux 6.18.20 | boot firmware, U-Boot, kernel, Debian or Alpine rootfs | booted on hardware (VAR-SOM on Symphony) |
| **STM32MP157F-DK2** | [`stm32mp1-dk2`](../boards/stm32mp1-dk2/README.md) | SD-card image (GPT) | upstream TF-A, OP-TEE, U-Boot 2026.07, Linux 6.18, 32-bit | firmware chain with OP-TEE, U-Boot, kernel, rootfs | built in a container; not yet booted on the kit |
| **STM32MP257F-DK** | [`stm32mp2-dk`](../boards/stm32mp2-dk/README.md) | SD-card image (GPT) | upstream stack, or ST's own tested set (`STACK=st`) | firmware chain with OP-TEE, U-Boot, kernel, rootfs | built in a container; not yet booted on the kit |
| **Zynq-7000** (Digilent Eclypse Z7) | [`zynq7000-eclypse-z7`](../boards/zynq7000-eclypse-z7/README.md) | SD-card image (MBR + `BOOT.BIN`) | mainline U-Boot (SPL as the first loader) and Linux 6.18 | `BOOT.BIN`, U-Boot, kernel, rootfs | built in a container, kernel and rootfs booted under QEMU; not yet booted on the board |
| **Jetson Orin Nano** (Developer Kit) | [`jetson-orin-nano`](../boards/jetson-orin-nano/README.md) | NVIDIA's flash tool over USB | NVIDIA Jetson Linux R36.4.3 (kernel 5.15) | kernel, NVIDIA modules, device trees, rootfs; boot firmware is NVIDIA's binary | recipe built in a container; not yet flashed on a kit |

Your PC: the four SD-card boards build on Ubuntu or Debian, x86-64 or ARM64, with about 15 GB free.
The Jetson needs Ubuntu 22.04 on **x86-64 only** and about 60 GB. Licences to accept: NXP's EULA (i.MX),
ST's DDR firmware licence (STM32), NVIDIA's licence (Jetson); the Zynq board downloads Digilent's board
file at build time.

The last column matters. Each board's README has its own status table that says exactly what was checked
and how; read it before you rely on a board. There are also ready-built images you can flash
without building: [download and flash](downloads.md).

## What each board teaches

### i.MX 8M Plus: the whole chain, on a board that is known to boot

Choose this one first. It has the most complete documentation (secure world, device-tree layers, a
source tour, a board tour, booting from eMMC), and it is the board whose build was run all the way to a
login prompt on real hardware. The boot chain is the classic one: ROM, a small U-Boot that trains the
DRAM, a secure monitor, U-Boot proper, Linux. If you want to understand what a Yocto BSP does, read this
one end to end.

### STM32MP2: a secure world you cannot skip, and a GPT image

Choose this one to see how a **trusted OS** and a **secure monitor** are a *requirement* rather than
an option: on this chip Linux asks OP-TEE for its clocks (SCMI). Everything is upstream and built
from source, including the firmware packaging (the FIP). It also teaches the other way of laying out
an SD card: a GPT disk whose partitions the ROM finds by *name*. It builds two software stacks, the
upstream one and ST's own tested set, so you can tell a board problem from a software problem.

### STM32MP1: the same family, 32 bits earlier

The STM32MP1 shares the vendor, the tools and the image format with the MP2, but is a 32-bit Cortex-A7
part: another toolchain, kernel image (`zImage`), device tree and partition names. Reading it next to the
MP2 is the quickest way to learn which parts of a boot chain are the SoC and which are the family. A chapter
in each directory compares them.

### Zynq-7000: a boot chain with no secure world, and an FPGA beside the CPU

Choose this one to see a boot where the first loader is a small build of U-Boot and the board's memory
and pin setup comes from a file the FPGA vendor's tools generate (`ps7_init`). It is also the board that
shows the processing-system and programmable-logic split, and where the Digilent Zmod add-on modules (such
as the Zmod ADC) would plug in. The first boot is the processing system only.

### Jetson Orin Nano: the vendor-flash model

Choose this one when your production board will boot from on-board flash, flashed by the vendor's
tool. You will not assemble an image; you will fill NVIDIA's staging tree with your kernel, device
tree and rootfs and flash over USB recovery mode. It also teaches that the first boot stages run on
other processors (the BPMP) and that part of the boot chain is a signed binary you replace rather than
rebuild. It needs a Linux x86-64 PC and is the heaviest download.

## A decision guide

| If you are… | Start with |
| --- | --- |
| new to embedded Linux and want the clearest tour | i.MX 8M Plus |
| curious how Trusted Firmware, OP-TEE and SCMI fit together | STM32MP2, then the i.MX 8M Plus secure-world chapter |
| comparing a 32-bit and a 64-bit chip of one family | STM32MP1 and STM32MP2 |
| working with an FPGA SoC | Zynq-7000 |
| bringing up a module that boots from on-board flash | Jetson Orin Nano, to learn the vendor-flash flow |
| choosing a SoC for a product | read all five boot chapters first: [the comparison](02-boot-chains-compared.md) |

## Adding another board

Pick the board whose *flashing model* matches yours, copy its directory, and follow
[the board contract](board-contract.md): same commands, pinned sources, numbered chapters, the four
required diagrams, and an honest status table.

Next: [05 · Glossary](05-glossary.md).
