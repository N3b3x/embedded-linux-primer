# 04 · The kernel

```bash
./build.sh kernel              # config + build + install   (the long step)
./build.sh kernel config       # only create .config
./build.sh kernel build        # only compile
./build.sh kernel install      # only collect zImage, DTB, modules into build/deploy/kernel/
./build.sh kernel-menuconfig   # interactive configuration
```

Script: [`scripts/kernel.sh`](../scripts/kernel.sh). Unlike the firmware, the kernel needs **no vendor
fork**: the STM32MP157 and this very board are supported by the mainline kernel.

## Which kernel

`KERNEL_VERSION=6.18.58`, a stable release tarball from `cdn.kernel.org`, pinned by sha256. A tarball is
about 150 MB; a full git history is several GB. The 6.18 series is a long-term-support series.

To move to another version, change `KERNEL_VERSION` and `KERNEL_SHA256` (the sums are published in
`sha256sums.asc` next to the tarballs); [10](10-versions.md) shows how.

## Configuration: the generic 32-bit `multi_v7_defconfig`

```text
make ARCH=arm CROSS_COMPILE=arm-none-linux-gnueabihf- LOCALVERSION=-custom multi_v7_defconfig
```

`arch/arm/configs/multi_v7_defconfig` is the configuration the kernel community maintains for **all**
mainline ARMv7 boards that can share one kernel binary. It is large (hundreds of drivers, most of them
modules), which is why the build is slow, but it works on every such board. It already contains
`ARCH_STM32=y` (and `MACH_STM32MP157=y` follows by default, `arch/arm/mach-stm32/Kconfig`).

> **Do not use `stm32_defconfig`.** It exists in the same directory but is the configuration of the STM32
> *microcontrollers* (Cortex-M, no MMU, no Linux userspace as you know it). It will not boot this MPU.

The script **checks** after creating `.config` that everything the boot path needs is built in, and stops with
an explanation if something is missing (a mistake in a fragment can silently switch one off). Verified on this
kernel: the unmodified `multi_v7_defconfig` already passes all 20 checks, so the shipped fragment is a
single line.

| Needed to reach a login | Option | Why |
| --- | --- | --- |
| the serial console | `SERIAL_STM32`, `SERIAL_STM32_CONSOLE` | `ttySTM0` is UART4, `drivers/tty/serial/stm32-usart.c` |
| the SD card | `MMC_ARMMMCI` (+ `MMC_STM32_SDMMC`) | the controller is an ARM PL18x variant, `drivers/mmc/host/mmci.c` |
| the root filesystem | `EXT4_FS`, `EFI_PARTITION` | ext4 root, `root=PARTUUID=` needs GPT parsing built in |
| device nodes | `DEVTMPFS`, `DEVTMPFS_MOUNT` | `/dev` exists before `init` |
| clocks, resets, regulators | `ARM_SCMI_PROTOCOL`, `ARM_SCMI_TRANSPORT_OPTEE`, `COMMON_CLK_SCMI`, `RESET_SCMI`, `REGULATOR_ARM_SCMI`, `TEE`, `OPTEE` | the secure world serves them ([11](11-secure-world-and-scmi.md)) |
| the clock controller | `COMMON_CLK_STM32MP157` | `drivers/clk/stm32/clk-stm32mp1.c` |
| pins | `PINCTRL_STM32MP157` | `drivers/pinctrl/stm32/pinctrl-stm32mp157.c` |
| the SoC's own regulators | `REGULATOR_STM32_PWR` | `pwr_regulators` in the device tree (`drivers/regulator/stm32-pwr.c`) |

They must be **built in** (`=y`), not modules: there is no initramfs, so the kernel has to read its root
filesystem before it can load a single module. That is the rule of thumb for anything between the CPU and
the root partition. Ethernet (`STMMAC_ETH`, `DWMAC_STM32`, `REALTEK_PHY`) is also built in by this
defconfig; the Wi-Fi driver (`BRCMFMAC`, with firmware you must supply) and the display (`DRM_STM`,
`DRM_PANEL_ORISETECH_OTM8009A`) are modules.

### The fragment

`config/kernel/*.cfg` files are merged on top with `scripts/kconfig/merge_config.sh` and the result is
re-resolved with `olddefconfig`. The shipped fragment is one line:

```text
# CONFIG_LOCALVERSION_AUTO is not set
```

It keeps `uname -r` at `6.18.58-custom` instead of appending a git hash that does not exist in a tarball.
`KERNEL_LOCALVERSION` is passed to *every* `make` call, because modules are installed under
`/lib/modules/<uname -r>` and must match the running kernel exactly.

## The device tree

The kernel's device-tree sources for this board are in `arch/arm/boot/dts/st/` (note `arm`, not `arm64`, and
the `st/` vendor directory):

| File | Role |
| --- | --- |
| `stm32mp157.dtsi`, `stm32mp151.dtsi` | the SoC: every peripheral, `status = "disabled"` by default |
| `stm32mp15xf.dtsi`, `stm32mp15xxac-pinctrl.dtsi`, `stm32mp15-pinctrl.dtsi` | the "F" variant (security + crypto + 800 MHz) and the package's pins |
| `stm32mp15xx-dkx.dtsi` | what the DK1 and DK2 boards share: memory, LED, SD card, Ethernet, UART4... |
| `stm32mp15-scmi.dtsi`, `stm32mp157f-dk2-scmi.dtsi` | the SCMI layer: clocks, resets and regulators come from OP-TEE |
| `stm32mp157f-dk2.dts` | **the board**: the DK2 with its display, touch panel, Wi-Fi and Bluetooth |

Together they say, among other things:

```dts
model = "STMicroelectronics STM32MP157F-DK2 Discovery Board";
compatible = "st,stm32mp157f-dk2", "st,stm32mp157";
aliases { serial0 = &uart4; ethernet0 = &ethernet0; };            /* from stm32mp15xx-dkx.dtsi */
chosen { stdout-path = "serial0:115200n8"; };
memory@c0000000 { reg = <0xc0000000 0x20000000>; };                /* 512 MiB */
reserved-memory { optee@de000000 { reg = <0xde000000 0x2000000>; no-map; }; };  /* 32 MiB */
&sdmmc1 { cd-gpios = <&gpiob 7 …>; bus-width = <4>; vmmc-supply = <&scmi_v3v3>; };
&i2c4 { status = "disabled"; };   /* "I2C4 is managed by OP-TEE" */
```

The `no-map` on the last 32 MiB keeps Linux away from OP-TEE's region ([01](01-boot-flow.md)).

(The kernel turns each `okay` node into a *device* and matches it against driver `compatible` strings:
`"st,stm32h7-uart"` → `stm32-usart.c`, `"arm,pl18x"` → `mmci.c`, `"st,stm32mp1-dwmac"` → `dwmac-stm32.c`.)

### One tree, and why no workaround

`KERNEL_DTBS=st/stm32mp157f-dk2.dtb` builds the stock tree and `extlinux.conf` names it. The 64-bit board
needs a device-tree workaround for its SD card supply; this one does not, because OP-TEE's STM32MP15 SCMI
server serves voltage domains ([11](11-secure-world-and-scmi.md#why-this-board-does-not-have-the-64-bit-boards-sd-card-problem)).
`custom/dts/` is empty for you to fill ([08](08-customizing.md)).

### The kernel command line

`root=PARTUUID=… console=ttySTM0,115200 rootwait rw earlycon`. `earlycon` (no argument) takes the UART from
`stdout-path`, so kernel messages appear from the first moment, before the serial driver has probed. A
bench-proven configuration of this kit uses the same `console=ttySTM0,115200 earlycon`.

## Build

```text
make … zImage modules                                # the kernel and its modules
make … st/stm32mp157f-dk2.dtb                        # the device tree
```

The first build is long because the defconfig builds a driver for many ARMv7 SoCs. On the machine described in [02](02-host-setup.md#disk-ram-time) it took **24 min 41 s** with 4 jobs
(a shared machine); an incremental rebuild including the install took 88 s. The result: `zImage` 11,911,680 bytes,
the DTB 55,849 bytes, 888 modules (33 MB stripped, 22 MB as a tarball). `ccache` makes the *second* build of the same version a
minute or two. To trim the build for your own product, start from `./build.sh kernel-menuconfig` and switch off
the `ARCH_*` platforms you do not have; `savedefconfig` produces a minimal fragment.

## Install

`./build.sh kernel install` collects, under `build/deploy/kernel/`:

```text
boot/zImage                      the kernel, compressed (U-Boot's bootz starts 32-bit ARM zImages as they are)
boot/stm32mp157f-dk2.dtb         the device tree extlinux.conf names
boot/config-6.18.58-custom       the .config it was built from
lib/modules/6.18.58-custom/…     modules, stripped (INSTALL_MOD_STRIP=1), host-only links removed
```

and a tarball `kernel-6.18.58-custom.tar.gz` of the same tree. `scripts/image.sh` unpacks it over the root
filesystem (with `--keep-directory-symlink`, because on Debian `/lib` is a symlink to `/usr/lib`). The
same tarball updates a card you already wrote: `./build.sh flash -d /dev/sdX --kernel-only`
([07](07-flashing-and-booting.md)).

Next: [05 · The root filesystem](05-rootfs.md).
