# 10 · Versions: what is pinned, why, and how to move

Every version lives in [`config/eclypse-z7.conf`](../config/eclypse-z7.conf). Software comes from **upstream**
(U-Boot's own repository, kernel.org), not from a vendor fork. The one non-software input is the board's PS7
initialisation file, pinned by commit and sha256.

## The pins

Current when the board was written (October 2026). Each one is a commit **and** a tag/version; the commit is what
is checked out, the tag is what a human reads.

| Part | Version | Pin | Where it came from |
| --- | --- | --- | --- |
| U-Boot | v2026.07 | commit `ece349ad…` | a release that has `xilinx_zynq_virt_defconfig` (SPL on), `CONFIG_XILINX_PS_INIT_FILE`, `tools/zynqimage.c`, and the `zynq-zybo-z7` tree this board's device tree was modelled on |
| PS7 init file | Digilent Eclypse-Z7-OS, commit `8d74b26e…`, `project-spec/hw-description/system.hdf` | sha256 `b7f74d49…` | the hardware handoff of the project that Digilent publishes for this board (Vivado 2019.1, board preset `digilentinc.com:eclypse-z7:1.0`); the same file a bench-proven configuration of this board uses |
| Linux | 6.18.58 | sha256 `069b19f9…` | newest 6.18 stable (a long-term series) when written; has `zynq-7000.dtsi`, `multi_v7_defconfig`, `zynq-fpga` |
| Arm GNU Toolchain | 14.3.rel1 `arm-none-linux-gnueabihf` | x86-64 sha256 `3ec0113a…`, ARM64 sha256 `547a618c…` | the `.sha256asc` files next to the downloads at `developer.arm.com/-/media/Files/downloads/gnu/14.3.rel1/binrel/` |
| Debian | trixie (13), `armhf` | `debian-archive-keyring` 2025.1, sha256 `9ea7778e…` | the stable release at the time; the 32-bit ARM hard-float port |
| Alpine | 3.24.2 `armv7` | `.sha256` fetched next to the file | |

The full 40-character commit and the sha256 values are in the config file. Check a pin yourself:

```bash
git ls-remote --tags https://github.com/u-boot/u-boot.git 'v2026.*'
curl -sI https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.18.58.tar.xz | head -1
curl -sL https://developer.arm.com/-/media/Files/downloads/gnu/14.3.rel1/binrel/arm-gnu-toolchain-14.3.rel1-x86_64-arm-none-linux-gnueabihf.tar.xz.sha256asc
sha256sum build/downloads/system.hdf
```

## Why these versions go together

* **U-Boot's Zynq-7000 support is generic.** One defconfig, the board chosen by `DEVICE_TREE`, the PS7 init
  file chosen by Kconfig. Nothing in it depends on the Linux version.
* **Linux and the device tree.** The board file `#include`s `zynq-7000.dtsi` of the *same* kernel (and of U-Boot's
  own copy for U-Boot): the two copies are close enough for one `.dts` to compile in both. If a future kernel
  renames a node, the kernel build fails at the DTB step and says which.
* **One toolchain.** A single `arm-none-linux-gnueabihf` compiler builds the SPL (bare metal in the on-chip RAM;
  it uses no libc), U-Boot proper and the kernel.
* **The PS7 file and the Vivado version.** The register values are Vivado 2019.1's. They describe hardware, not
  software: a different Vivado version would write the same board's values in a different style. What must not change
  is the board preset (DDR part, clock, MIO map).

## Moving to a newer release

| To move | Do |
| --- | --- |
| U-Boot | `git ls-remote --tags https://github.com/u-boot/u-boot.git`; set `UBOOT_BRANCH` and `UBOOT_REV` (the commit of the tag, with `^{}` for annotated tags) in `config/local.conf`; check that `configs/xilinx_zynq_virt_defconfig` and `board/xilinx/zynq/` still exist; `./build.sh uboot`; check the `mkimage -l` header and the 192 KiB limit |
| Linux | pick a version on kernel.org, set `KERNEL_VERSION` and `KERNEL_SHA256` (from `sha256sums.asc` next to the tarball); `./build.sh kernel`; the symbol check and the DTB build tell you what moved. For another series, check `arch/arm/boot/dts/xilinx/` first |
| Toolchain | set `ARM_TOOLCHAIN_VERSION` and both sha256 values from the `.sha256asc` of the new release |
| Debian suite | `DEBIAN_SUITE`; if its archive key is new, update `DEBIAN_KEYRING_URL` and its sha256 |
| PS7 file | `PS7_INIT_SRC=…` (your own design), or a new pinned URL and sha256 |

`--update` re-fetches a pinned git source that already exists (and refuses if it has local changes).

## Plan B: the vendor stack

If the open path will not boot on your board and you need a known-good reference quickly, Digilent publishes a
Debian SD-card image for the Eclypse Z7 (releases of `Digilent/Eclypse-Z7` on GitHub: look at the tag's *Assets*,
not the newest release, which is a hardware demo). It uses Xilinx's FSBL, Digilent's U-Boot and a PetaLinux
kernel. Booting that image once proves the board, the power, the jumper and the serial cable; it is a diagnostic
step, not a base for this repository.

Next: [11 · The processing system and the programmable logic](11-ps-and-pl.md).
