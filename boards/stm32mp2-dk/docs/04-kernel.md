# 04 · The kernel

```bash
./build.sh kernel              # config + build + install   (the long step)
./build.sh kernel config       # only create .config
./build.sh kernel build        # only compile
./build.sh kernel install      # only collect Image, DTBs, modules into build/deploy/kernel/
./build.sh kernel-menuconfig   # interactive configuration
```

Script: [`scripts/kernel.sh`](../scripts/kernel.sh). Unlike the firmware, the kernel needs **no vendor
fork**: the STM32MP25 and this very board are supported by the mainline kernel.

## Which kernel

`KERNEL_VERSION=6.18.58`, a stable release tarball from `cdn.kernel.org`, pinned by sha256. A tarball is
about 150 MB; a full git history is several GB. The 6.18 series is a long-term-support series.

To move to another version, change `KERNEL_VERSION` and `KERNEL_SHA256` (the sums are published in
`sha256sums.asc` next to the tarballs); [10](10-versions.md) shows how.

## Configuration: the generic arm64 `defconfig`

```text
make ARCH=arm64 CROSS_COMPILE=aarch64-none-linux-gnu- LOCALVERSION=-custom defconfig
```

`arch/arm64/configs/defconfig` is the one configuration the kernel community maintains for **all**
mainline arm64 boards. It is large (hundreds of drivers, most of them modules), which is why the build is
slow, but it works on every board and lets you plug in USB devices and load their drivers.

For *this* board the defconfig already enables everything the boot path needs. The script **checks** that
after creating `.config` and stops with an explanation if something is missing (a mistake in a fragment
can silently switch one off):

| Needed to reach a login | Option | Why |
| --- | --- | --- |
| the serial console | `SERIAL_STM32`, `SERIAL_STM32_CONSOLE` | `ttySTM0` is USART2, `drivers/tty/serial/stm32-usart.c` |
| the SD card | `MMC_ARMMMCI` (+ `MMC_STM32_SDMMC`) | the controller is an ARM PL18x variant, `drivers/mmc/host/mmci.c` |
| the root filesystem | `EXT4_FS`, `EFI_PARTITION` | ext4 root, `root=PARTUUID=` needs GPT parsing built in |
| device nodes | `DEVTMPFS`, `DEVTMPFS_MOUNT` | `/dev` exists before `init` |
| clocks and resets | `ARM_SCMI_PROTOCOL`, `ARM_SCMI_TRANSPORT_OPTEE`, `COMMON_CLK_SCMI`, `RESET_SCMI`, `OPTEE` | the secure world serves them ([11](11-secure-world-and-scmi.md)) |
| the clock controller | `COMMON_CLK_STM32MP257` | `drivers/clk/stm32/clk-stm32mp25.c` |
| pins | `PINCTRL_STM32MP257` | `drivers/pinctrl/stm32/pinctrl-stm32mp257.c` |

They must be **built in** (`=y`), not modules: there is no initramfs, so the kernel has to read its root
filesystem before it can load a single module. That is the rule of thumb for anything between the CPU and
the root partition. Ethernet (`STMMAC_ETH`, `DWMAC_STM32`, `REALTEK_PHY`) is a module in the defconfig:
Debian's `udev` loads it from the root filesystem.

### The fragment

`config/kernel/*.cfg` files are merged on top with `scripts/kconfig/merge_config.sh` and the result is
re-resolved with `olddefconfig`. The shipped fragment is one line:

```text
# CONFIG_LOCALVERSION_AUTO is not set
```

It keeps `uname -r` at `6.18.58-custom` instead of appending a git hash that does not exist in a tarball.
`KERNEL_LOCALVERSION` is passed to *every* `make` call, because modules are installed under
`/lib/modules/<uname -r>` and must match the running kernel exactly.

The fragment also keeps the open-source Vivante GPU driver out of the kernel:

```text
# CONFIG_DRM_ETNAVIV is not set
```

On ST's device tree the GPU node is enabled, and loading that driver makes it request the GPU's clock over SCMI,
which crashed OP-TEE 4.0 on the bench. The mainline 6.18 trees of this board have no GPU node, so the driver
would have nothing to bind to anyway; the line only makes sure it cannot wake up if someone adds one.

## The kernel of `-s st`

`./build.sh -s st kernel` builds ST's Linux 6.6 instead: the git tag `v6.6-stm32mp-r3` (kernel.org 6.6.116 plus ST's
patch series), fetched as one shallow commit into `build/src-st/linux-6.6-stm32mp-r3`. Differences in the recipe:

* **Configuration**: the same arm64 `defconfig`, then ST's four fragments in ST's order (`fragment-01-defconfig-cleanup`
  and `fragment-02-defconfig-addons` from the kernel tree, `fragment-03-systemd` and `fragment-04-modules`
  downloaded from ST's Yocto layer at a pinned commit, sha256-checked), then your `config/kernel/*.cfg`.
  The boot-path check passes with the 17 options above plus `REGULATOR_ARM_SCMI` (the SD card's supply is an SCMI
  regulator in ST's tree): 18. Ethernet (`DWMAC_STM32`) is a module here too.
* **Device tree**: not in the kernel tree but in ST's `dt-stm32mp` repository. ST's kernel Makefile looks for
  `st/stm32mp257f-dk-ca35tdcid-ostl.dtb` in the tree first and then in `KBUILD_EXTDTS`, which the script points at
  `stm32mp2/a35-td/linux`. The tree's SD card supplies are SCMI regulators that ST's OP-TEE serves: no workaround
  tree. Your own additions go to `custom/dts-st/`.
* **Size and time**: `Image` of 25,704,960 bytes, 6.6.116-custom, about 25 minutes with 4 jobs.
* **Command line**: `rootwait rw earlycon modprobe.blacklist=etnaviv` (and no `rootflags=`), see
  [15](15-two-stacks.md#device-trees-one-description-or-four).

## The device tree

The kernel's device-tree sources for this board are in `arch/arm64/boot/dts/st/`:

| File | Role |
| --- | --- |
| `stm32mp257.dtsi`, `stm32mp251.dtsi` | the SoC: every peripheral, `status = "disabled"` by default |
| `stm32mp25xf.dtsi`, `stm32mp25xxal-pinctrl.dtsi`, `stm32mp25-pinctrl.dtsi` | the "F" variant (security + crypto) and the package's pins |
| `stm32mp257f-dk.dts` | **the board**: what is wired and enabled |

`stm32mp257f-dk.dts` says, among other things:

```dts
model = "STMicroelectronics STM32MP257F-DK Discovery Board";
compatible = "st,stm32mp257f-dk", "st,stm32mp257";
aliases { ethernet0 = &ethernet1; serial0 = &usart2; };
chosen { stdout-path = "serial0:115200n8"; };
memory@80000000 { reg = <0x0 0x80000000 0x1 0x0>; };            /* 4 GiB */
reserved-memory { fw@80000000 { reg = <0x0 0x80000000 0x0 0x4000000>; no-map; }; };  /* 64 MiB */
```

and enables `&ethernet1` (RGMII, a Realtek PHY), `&sdmmc1` (the microSD slot), `&usart2` (the console),
the blue heartbeat LED and two user buttons. `no-map` on the first 64 MiB keeps Linux away from the
OP-TEE region inside it ([01](01-boot-flow.md)).

(The kernel turns each `okay` node into a *device* and matches it against driver `compatible` strings:
`"st,stm32h7-uart"` → `stm32-usart.c`, `"st,stm32mp25-sdmmc2"` / `"arm,pl18x"` → `mmci.c`,
`"st,stm32mp25-dwmac"` → `dwmac-stm32.c`.)

### Two trees are installed; the first is booted, the second is a menu entry

`KERNEL_DTBS` builds two files. `/boot/extlinux/extlinux.conf` names the first as the default entry and the
second as another boot-menu entry (U-Boot shows the menu for three seconds; press a key on the serial console
and choose entry 2):

| File | What |
| --- | --- |
| `stm32mp257f-dk-primer.dtb` | **booted by default**: the stock tree with the SD card's supplies replaced by fixed regulators, source in [`custom/dts/stm32mp257f-dk-primer.dts`](../custom/dts/stm32mp257f-dk-primer.dts) |
| `stm32mp257f-dk.dtb` | the unmodified upstream tree: the second boot-menu entry, to compare on the board |

Why a workaround is needed is explained in
[09 · Troubleshooting](09-troubleshooting.md#linux-never-finds-the-root-filesystem) and
[11](11-secure-world-and-scmi.md#what-this-repository-had-to-work-around): the upstream tree gets the SD
card's power from an SCMI *voltage domain*, which the all-upstream OP-TEE built here does not provide.
**This is the least certain part of the board** and has not been tried on hardware. Boot the stock
tree from the menu (or move it first in `KERNEL_DTBS`) if your firmware does serve voltage domains, and use
`-s st` ([15](15-two-stacks.md)) if you want the combination in which the supply is served.

## Build

```text
make … Image modules                                 # the kernel and 1,418 modules
make … st/stm32mp257f-dk-primer.dtb st/stm32mp257f-dk.dtb   # the device trees
```

The first build is long because the defconfig builds a driver for nearly every arm64 SoC on the market
(`CONFIG_ARCH_*`). On the machine described in [02](02-host-setup.md) it took **36 minutes** with
6 jobs (the machine was shared with other jobs; a rebuild after touching a fragment or a device tree took 35 s). `ccache` makes the *second* build of the same version a minute or two. To trim the build for your
own product, start from `./build.sh kernel-menuconfig` and switch off the `ARCH_*` platforms you do not
have; `savedefconfig` produces a minimal fragment.

## The kernel command line

`scripts/image.sh` writes `root=PARTUUID=<rootfs> <KERNEL_CMDLINE_EXTRA> console=ttySTM0,115200`, with
`KERNEL_CMDLINE_EXTRA="rootwait rw earlycon"` (the ST stack adds `modprobe.blacklist=etnaviv`):

| Part | What it does |
| --- | --- |
| `root=PARTUUID=…` | the root by its GPT identifier, independent of `mmcblk0`/`mmcblk1` |
| `rootwait` | wait for the SD card to appear instead of panicking |
| `rw` | mount the root read-write |
| `earlycon` | print kernel messages through the UART that the device tree's `stdout-path` names, **before** the real serial driver is up, so a kernel that dies early still leaves a trace |
| `console=ttySTM0,115200` | the real console, USART2 |

## Install

`./build.sh kernel install` collects, under `build/deploy/kernel/`:

```text
boot/Image                       the kernel, uncompressed (U-Boot's booti loads arm64 Images as they are)
boot/stm32mp257f-dk-primer.dtb   boot/stm32mp257f-dk.dtb
boot/config-6.18.58-custom       the .config it was built from
lib/modules/6.18.58-custom/…     modules, stripped (INSTALL_MOD_STRIP=1), host-only links removed
```

and a tarball `kernel-6.18.58-custom.tar.gz` of the same tree. `scripts/image.sh` unpacks it over the root
filesystem (with `--keep-directory-symlink`, because on Debian `/lib` is a symlink to `/usr/lib`). The
same tarball updates a card you already wrote: `./build.sh flash -d /dev/sdX --kernel-only`
([07](07-flashing-and-booting.md)).

Next: [05 · The root filesystem](05-rootfs.md).
