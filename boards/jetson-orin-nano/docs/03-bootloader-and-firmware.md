# 03 · Boot firmware: what NVIDIA ships and what you can steer

[Docs](README.md) › **03 · Boot firmware**

On the SD-card boards of this repository the bootloader chapter is about *compiling* U-Boot and TF-A.
On the Jetson it is about *selecting and configuring* binaries that NVIDIA delivers. This chapter shows where those
binaries are, what configures them, and which knobs are safe for a first project.

## 1. What is in the driver package

`Jetson_Linux_r36.4.3_aarch64.tbz2` unpacks into `Linux_for_Tegra/`. The parts that matter here:

| Path | What it is |
| --- | --- |
| `bootloader/mb1_t234_prod.bin`, `mb2_t234.bin`, `psc_bl1_t234_prod.bin`, `pscfw_t234_prod.bin` | MB1, MB2 and the platform security controller's firmware: NVIDIA binaries, signed |
| `bootloader/uefi_jetson.bin` | UEFI, the CPU bootloader |
| `bootloader/tos-optee_t234.img` | the secure OS image (OP-TEE on Arm Trusted Firmware) |
| `bootloader/bpmp_t234-*.bin`, `spe_t234.bin`, `camera-rtcpu-t234-rce.img`, `display-t234-dce.bin`, `adsp-fw.bin`, `nvpva_020.fw` … | firmware for the other processors |
| `bootloader/BOOTAA64.efi` | L4TLauncher, UEFI's default OS loader |
| `bootloader/generic/BCT/*.dtsi` | the **boot configuration tables**, as device-tree source: pinmux, pad voltages, GPIO, PMIC |
| `bootloader/generic/cfg/flash_t234_qspi*.xml` | partition layouts: which image goes where |
| `jetson-orin-nano-devkit*.conf`, `p3768-…conf`, `p3767.conf.common` | **board specifications**: which of the above a given module + carrier uses |
| `kernel/`, `rootfs/` | a prebuilt kernel and the (empty until you fill it) root filesystem |
| `flash.sh`, `tools/kernel_flash/` | the flash tools |

You can *read* the BCTs and the board files. You cannot read MB1: it is a binary, signed and encrypted by NVIDIA. NVIDIA's
Developer Guide describes the BCTs as the way to configure it for a platform.

## 2. A board specification, read line by line

`jetson-orin-nano-devkit-super.conf` is short because it builds on others:

```text
source "${LDK_DIR}/p3768-0000-p3767-0000-a0.conf";      # the carrier + module family
p3767_super_overlay() { … picks BPFDTB_FILE and DTB_FILE per module SKU … }
update_flash_args() { update_flash_args_common; p3767_super_overlay }
```

and that file sources `p3767.conf.common`, which names the binary for **every** partition of the module.
A few lines from it, as shipped:

```text
CHIPID=0x23;
OVERLAY_DTB_FILE="L4TConfiguration.dtbo,tegra234-carveouts.dtbo,tegra-optee.dtbo";
CMDLINE_ADD="… console=ttyTCU0,115200 … console=tty0"
ROOTFSSIZE=55GiB;
MB1FILE="bootloader/mb1_t234_prod.bin";
TBCFILE="bootloader/uefi_jetson.bin";
TOSFILE="bootloader/tos_t234.img";
PINMUX_CONFIG="tegra234-mb1-bct-pinmux-p3767-dp-a03.dtsi";
```

Notice:

- **`OVERLAY_DTB_FILE`** lists device-tree *overlays* UEFI applies at boot. `L4TConfiguration.dtbo` is where the boot mode
  and boot order live; the boot-order file this repository adds via `ADDITIONAL_DTB_OVERLAY_OPT` is appended to this list (`flash.sh`).
- **`CMDLINE_ADD`** is the part of the kernel command line that NVIDIA's board file contributes. The default console is
  **`ttyTCU0`**, the Tegra Combined UART, which the SoC multiplexes onto the debug UART path.
- **`ROOTFSSIZE=55GiB`** is the default size of the root partition (`APP`). Override with `APP_SIZE` in `config/local.conf`
  (passed as `-S`).
- The module SKU decides the device tree: for the Super configuration, SKU `0005` (the Orin Nano 8GB developer module)
  uses `tegra234-p3768-0000+p3767-0005-nv-super.dtb`, with the BPMP device tree of SKU `0003`.

## 3. Which board name?

| `BOARD` | Meaning (NVIDIA's Quick Start) |
| --- | --- |
| `jetson-orin-nano-devkit-super` | Orin Nano / NX modules on the P3768 carrier, with the higher power budget and extended clock steps of the *Super* configuration. **Default here** |
| `jetson-orin-nano-devkit` | same hardware, original power modes |

The files `jetson-orin-nano-devkit-nvme.conf` and `jetson-orin-nano-devkit-super-nvme.conf` also exist in R36.4.3. They are the same
configurations with the NVMe partition layout selected in the board file. NVIDIA's Quick Start uses the plain names and
selects the storage with `--external-device`, which is what `./build.sh` does for all three root devices.

## 4. UEFI variables are a device tree overlay

UEFI's settings for this release are carried as overlays. You can read the default ones in plain text:

```bash
cd build/work/Linux_for_Tegra
kernel/dtc -I dtb -O dts kernel/dtb/L4TConfiguration.dtbo       # or the dtc from device-tree-compiler
```

What it shows (R36.4.3, abbreviated):

```text
L4TDefaultBootMode      { data = <0x1000000>; … }        /* bytes 01 00 00 00: kernel + DTB in the filesystem */
RootfsRetryCountMax     { data = <0x3000000>; … }        /* 3 */
DefaultBootPriority     { data = "usb,nvme,emmc,sd,ufs"; locked; }
```

and the overlay this repository adds for an NVMe root, `BootOrderNvme.dtbo`:

```text
overlay-name = "UEFI Boot order nvme default";
… DefaultBootPriority { data = "nvme"; locked; } …
```

To change the default boot mode instead of the order, NVIDIA's procedure is: convert `L4TConfiguration.dtbo` to `.dts` with
`kernel/dtc`, edit the `L4TDefaultBootMode` bytes, convert back, then flash again (*UEFI*, "Customizing the Default Boot
Mode"). It lands in the QSPI-NOR flash, so it needs recovery mode ([11](11-recovery-and-usb-flash.md)).

## 5. The secure OS and the other open sources

`public_sources.tbz2` contains the sources of the secure OS, so you can see how `tos-optee_t234.img` is made:

| Archive in `source/` | Contents |
| --- | --- |
| `atf_src.tbz2` | `arm-trusted-firmware/` |
| `nvidia-jetson-optee-source.tbz2` | `optee/optee_os`, `optee_client`, `optee_test`, `tegra234-optee.dts` and a README |
| `spe-freertos-bsp.tbz2` | FreeRTOS for the SPE (`spe_t234.bin`) |

UEFI's source is on GitHub: [NVIDIA/edk2-nvidia](https://github.com/NVIDIA/edk2-nvidia). NVIDIA's *UEFI* chapter explains how to rebuild it and where the
rebuilt `L4TConfiguration.dtbo` goes. This repository does not build any of these: they are the place to go after the first steps.

## 6. Updating the firmware of a running board

Two mechanisms, both from NVIDIA's *Update and Redundancy* chapter:

- **Flash again** from recovery mode (what `./build.sh flash` does). Rewrites everything it is given.
- **UEFI capsule updates**, applied by UEFI to the *non-current* slot on the next boot, or the Debian package
  `nvidia-l4t-bootloader` on a running system (`sudo dpkg-reconfigure nvidia-l4t-bootloader`; NVIDIA's text for JetPack 5 to 6 migration shows it).
  Check with `sudo nvbootctrl dump-slots-info`.

## 7. Secure boot and fuses (read before you experiment)

NVIDIA's *Secure Boot* chapters describe how to sign and encrypt the boot chain with fused keys (PKC, SBK).
**Burning fuses is irreversible.** Nothing in this repository fuses a device; the flash command used here is the
unfused development flow. If you plan production, read NVIDIA's documentation and the `odmfuse.sh` notes first,
on a board you can afford to lose.

Next: [04 · Kernel](04-kernel.md) · Prev: [02 · Host setup](02-host-setup.md)
