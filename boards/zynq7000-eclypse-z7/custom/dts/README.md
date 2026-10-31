# custom/dts/

`zynq-eclypse-z7.dts` is the board's device tree. **One file serves two projects**: `scripts/uboot.sh` copies it into
`arch/arm/dts/` of U-Boot, `scripts/kernel.sh` into `arch/arm/boot/dts/xilinx/` of the kernel. Both trees have a
`zynq-7000.dtsi` it `#include`s. Nodes the SPL needs (UART, SD host, QSPI) carry `bootph-all`, which Linux ignores.

Mainline U-Boot and Linux have device trees for other Zynq boards (`zynq-zybo-z7`, `zynq-zed`, …) but none for the
Eclypse Z7; this one is written from Digilent's reference manual and the Vivado board preset, and its Ethernet and SD
parts follow the Zybo Z7 tree of the same SoC.

Any other `*.dts` / `*.dtsi` you drop here is copied into the kernel tree and every `*.dts` is built; to boot yours,
put its `.dtb` **first** in `KERNEL_DTBS` (`config/local.conf`):

```bash
KERNEL_DTBS="xilinx/my-board.dtb xilinx/zynq-eclypse-z7.dtb"
```

Remember to rebuild U-Boot too when you change a node it uses (`./build.sh uboot`).
See `docs/08-customizing.md`.
