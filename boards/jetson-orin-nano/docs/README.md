# Documentation

> NVIDIA Jetson Orin Nano Developer Kit · Jetson Linux R36.4.3. Read in order the first time; afterwards jump to what you need.

The chapters follow the boot, as on every board of this repository ([the board contract](../../../docs/board-contract.md)).
Chapters 11-15 are specific to this board and its flashing model.

| # | Chapter | You learn |
| --- | --- | --- |
| 01 | [Boot flow](01-boot-flow.md) | every stage from the BootROM to a login, which processor runs it and where it is stored |
| 02 | [Host setup](02-host-setup.md) | the x86-64 PC, the cables, the packages, how to check them |
| 03 | [Boot firmware](03-bootloader-and-firmware.md) | what NVIDIA ships as binaries, the board specification, UEFI's settings as overlays |
| 04 | [Kernel](04-kernel.md) | the four products of a Jetson kernel build, config fragments, patches, device trees |
| 05 | [Root filesystem](05-rootfs.md) | sample rootfs + NVIDIA userspace + a login account, and how to modify it |
| 06 | [Flash package](06-flash-package.md) | the partition files, what `image` generates, online vs offline |
| 07 | [Flashing & first boot](07-flashing-and-booting.md) | recovery mode, the flash, what a healthy first login looks like |
| 08 | [Customizing](08-customizing.md) | where each kind of change goes; your own carrier; the fast kernel loop |
| 09 | [Troubleshooting](09-troubleshooting.md) | symptoms with the exact messages the tools print |
| 10 | [Versions](10-versions.md) | what is pinned, checksums, how to move to another release |
| 11 | [Recovery mode and the USB flash](11-recovery-and-usb-flash.md) | the flash protocol step by step: RCM boot, USB Ethernet, SSH, NFS |
| 12 | [Board tour](12-board-tour.md) | module and carrier, what "Super" means in the files, power modes |
| 13 | [SD card vs vendor flash](13-sd-card-vs-vendor-flash.md) | the two flashing models compared |
| 14 | [Acronyms](14-acronyms.md) | BPMP, PSC, MB1, MB2, UEFI, RCM, BCT … |
| 15 | [Source tour](15-source-tour.md) | the real files, with excerpts, in boot order |

Diagrams (SVG, regenerated from Python): [images/README.md](images/README.md).

## Three ways to read

- **"I want the board running."** [README](../README.md) quick start → [02](02-host-setup.md) → [07](07-flashing-and-booting.md) → [09](09-troubleshooting.md).
- **"I want to understand how it boots."** [01](01-boot-flow.md) → [13](13-sd-card-vs-vendor-flash.md) → [03](03-bootloader-and-firmware.md) → [15](15-source-tour.md).
- **"I want my own kernel and device tree."** [04](04-kernel.md) → [08](08-customizing.md) → [12](12-board-tour.md).

## How sure is this?

The [README status table](../README.md#what-has-been-verified) says which parts were run and which were only cross-checked against NVIDIA's
documentation and scripts. Chapters repeat the caveat where it matters. NVIDIA's own Developer Guide for R36.4.3 is the authority; this
manual explains it through scripts you can run.
