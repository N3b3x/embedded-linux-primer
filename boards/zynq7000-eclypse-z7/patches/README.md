# patches/

Put `*.patch` files (from `git format-patch`/`git diff`, or `diff -u` with `a/` and `b/` prefixes) in the subfolder of the component they change:

| Folder | Applied to | When |
| --- | --- | --- |
| `u-boot/` | `build/src/u-boot` | `./build.sh uboot` |
| `kernel/` | `build/src/linux-<version>` | `./build.sh kernel` |

They are applied in file-name order, once per checkout (the names are remembered inside the checkout).

## What is here

Each tree has one patch, and it does one thing: the board's device tree is a file in `custom/dts/`, and the patch
adds `zynq-eclypse-z7.dtb` to the Makefile of the device-tree directory so that the normal build rule applies.

| Patch | Effect |
| --- | --- |
| `u-boot/0001-arm-dts-zynq-build-the-Eclypse-Z7-device-tree.patch` | `arch/arm/dts/Makefile`: `zynq-eclypse-z7.dtb` in the `CONFIG_ARCH_ZYNQ` list |
| `kernel/0001-ARM-dts-xilinx-build-the-Eclypse-Z7-device-tree.patch` | `arch/arm/boot/dts/xilinx/Makefile`: the same |

See `docs/08-customizing.md`.
