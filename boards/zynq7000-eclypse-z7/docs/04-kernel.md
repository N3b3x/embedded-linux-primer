# 04 · The kernel

What `./build.sh kernel` builds, which defconfig and device tree it uses, and why.

| | |
| --- | --- |
| Source | `linux-6.18.58.tar.xz` from kernel.org (sha256 pinned), unpacked to `build/src/linux-6.18.58` |
| Architecture | 32-bit ARM, `ARCH=arm`, compiler `arm-none-linux-gnueabihf-` (Arm GNU Toolchain 14.3) |
| Configuration | `multi_v7_defconfig` + `config/kernel/*.cfg` |
| Result | `zImage` (11.9 MB), `zynq-eclypse-z7.dtb` (11 KB), about 890 modules (33 MB), the `.config` |
| Version string | `6.18.58-custom` (`KERNEL_LOCALVERSION`, no git hash appended) |
| First build time | 18 minutes (4 jobs, container sharing an 11-core machine); a rebuild after a one-file change takes seconds |

## Why `multi_v7_defconfig`

The mainline kernel has **no** `xilinx_zynq_defconfig`. (Xilinx's own tree, `linux-xlnx`, has one; this repository
uses mainline.) The generic 32-bit ARMv7 defconfig `multi_v7_defconfig` builds one kernel for dozens of Cortex-A
SoCs, and it enables `ARCH_ZYNQ`, the Zynq clock and timer drivers, the PS UART, the Arasan SD controller, the
Cadence GEM (`macb`) and the Realtek PHY driver as **built-in** drivers. The price is time and space: it builds
drivers for hardware you do not have. To make a leaner kernel, start from `multi_v7_defconfig` with
`./build.sh kernel-menuconfig` and turn things off ([08](08-customizing.md)).

### The boot path must be built in

There is no initramfs. The kernel has to read its root file system before it can load a single module, so
everything between the CPU and the root partition must be `=y`, not `=m`. `scripts/kernel.sh` checks 14
symbols after every configuration and stops if one is missing:

| Symbol | What it is for |
| --- | --- |
| `ARCH_ZYNQ` | the SoC: clocks, SLCR, timers, SMP |
| `SERIAL_XILINX_PS_UART`, `SERIAL_XILINX_PS_UART_CONSOLE` | the console on `ttyPS0`, and `earlycon` |
| `MMC_SDHCI`, `MMC_SDHCI_PLTFM`, `MMC_SDHCI_OF_ARASAN` | the SD controller that holds the root file system |
| `MSDOS_PARTITION` | reading the MBR, needed for `root=PARTUUID=` |
| `EXT4_FS`, `VFAT_FS` | the root file system, and the FAT boot partition |
| `DEVTMPFS`, `DEVTMPFS_MOUNT` | `/dev` before init runs |
| `MACB`, `REALTEK_PHY` | Ethernet MAC and the board's RTL8211E PHY |
| `GPIO_ZYNQ` | the PS GPIO controller (the PHY and USB reset lines) |

### One fragment: `config/kernel/00-base.cfg`

* `# CONFIG_LOCALVERSION_AUTO is not set`: keeps `uname -r` stable.
* `CONFIG_FPGA=y` and `CONFIG_FPGA_MGR_ZYNQ_FPGA=m`: the FPGA manager driver for `devcfg`. It is a module and
  nothing loads a bitstream at boot; it is there for chapter [13](13-zmod-adc.md).

## The device tree

Mainline Linux 6.18 has trees for several Zynq boards (`zynq-zybo-z7.dts`, `zynq-zed.dts`, `zynq-microzed.dts`,
…) but none for the Eclypse Z7. `custom/dts/zynq-eclypse-z7.dts` is therefore part of this repository, and
`scripts/kernel.sh` copies it to `arch/arm/boot/dts/xilinx/` before building. A one-line patch
(`patches/kernel/0001-…patch`) adds `zynq-eclypse-z7.dtb` to that directory's Makefile, so the kernel's normal
`make xilinx/zynq-eclypse-z7.dtb` works.

What the file says (all of it is wiring that comes from the board's reference manual and the Vivado board preset
for it):

| Node | Setting | Why |
| --- | --- | --- |
| `memory@0` | 1 GiB at 0 | DDR3L on the board |
| `chosen` | `stdout-path = "serial0:115200n8"`, `serial0 = &uart0` | console and `earlycon` find the right UART |
| `&clkc` | `ps-clk-frequency = <33333333>` | the board's PS_CLK oscillator; every other clock derives from it |
| `&uart0` | okay | MIO 14/15 → FT2232HQ USB-UART |
| `&sdhci0` | okay, `disable-wp` | microSD slot J4 (a microSD slot has no write-protect switch) |
| `&gem0` + `ethernet-phy@1` | RGMII with internal delay (`rgmii-id`), PHY address 1, reset on MIO 9 | RTL8211E-VL PHY |
| `&usb0` + `phy0` | host mode, reset on MIO 46 | USB OTG connector |
| `&gpio0`, `&i2c1`, `&qspi` | okay | PHY/USB resets, the platform MCU, the flash (it holds the factory MAC) |
| `&devcfg`, `fpga_full` | from `zynq-7000.dtsi` | the FPGA manager and its region, for chapter 13 |

The MIO **pin muxing** is not in the device tree: on the Zynq it is set by the PS7 initialisation that the SPL
ran ([03](03-uboot-spl.md)). The kernel finds the pins already configured.

Things you will notice on the running board: the Ethernet interface is called `end0` (systemd's predictable
name; `eth0` until udev renames it); the MAC address is random, **not** the factory address stored in the QSPI
flash's OTP area (reading it needs U-Boot or a small tool; see the board reference manual) so give the board a
fixed address in your DHCP server if that matters.

## The kernel command line

Written by `scripts/image.sh` into `extlinux.conf`:

```text
root=PARTUUID=5a796e71-02 console=ttyPS0,115200 rootwait rw earlycon
```

| Part | Meaning |
| --- | --- |
| `root=PARTUUID=5a796e71-02` | the second partition of the disk whose MBR signature is `5a796e71`: found on any mmc number |
| `console=ttyPS0,115200` | kernel messages and the login go to PS UART0 |
| `rootwait` | wait for the SD card to appear instead of failing at once |
| `rw` | mount the root read-write (the Debian `fstab` remounts it by label) |
| `earlycon` | print from the first instruction using the UART named by `stdout-path`; a **first-boot aid**, remove it with `KERNEL_CMDLINE_EXTRA="rootwait rw"` once the board boots |

## Installed files

`scripts/kernel.sh install` leaves two halves in `build/deploy/kernel/` (and one tarball of both, for updating a
card in place):

```text
fat/zImage                  → the FAT partition
fat/zynq-eclypse-z7.dtb     → the FAT partition
rootfs/boot/config-6.18.58-custom
rootfs/lib/modules/6.18.58-custom/…   → the ext4 partition
```

`./build.sh flash -d /dev/sdX --kernel-only` copies them to a card you already wrote.

## Move to another version

See [10](10-versions.md). The device tree and `multi_v7_defconfig` have been stable across 6.x; the quickest check
after a version bump is `./build.sh kernel config` (it runs the symbol check) and a build of the DTB.

Next: [05 · The root filesystem](05-rootfs.md).
