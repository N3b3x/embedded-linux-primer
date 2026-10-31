# config/uboot/

U-Boot configuration fragments: every `*.config` here is merged on top of `xilinx_zynq_virt_defconfig` by
`scripts/uboot.sh`, followed by one generated line (`CONFIG_XILINX_PS_INIT_FILE`). Same format as the kernel's:
`CONFIG_FOO=y`, or `# CONFIG_FOO is not set`.

`eclypse-z7.config` selects the device tree and sets a few strings. Use `./build.sh uboot-menuconfig` to find option
names, then put the lines you want to keep in a new `NN-name.config` here. Remember that the SPL must stay below 192 KiB
(`scripts/uboot.sh` checks).
