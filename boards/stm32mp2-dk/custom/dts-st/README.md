# custom/dts-st/

Your own device trees for the **ST stack** (`./build.sh -s st`). Files `*.dts` / `*.dtsi` placed here are copied
into `arch/arm64/boot/dts/st/` of ST's kernel before it is built, and every `*.dts` is built into a `.dtb`
that is installed in `/boot`. They can `#include` ST's files, for example
`#include "stm32mp257f-dk-ca35tdcid-ostl.dts"` (that tree comes from ST's `dt-stm32mp` repository, which the
kernel build is pointed at).

To boot your tree, put it **first** in `KERNEL_DTBS` (`config/local.conf`); `scripts/image.sh` writes it as the
default entry of `extlinux.conf`:

```bash
KERNEL_DTBS="st/my-board.dtb st/stm32mp257f-dk-ca35tdcid-ostl.dtb"
```

It is empty by default: ST's tree already describes the SD card's supplies as SCMI regulators that ST's OP-TEE
provides, so the workaround of [`../dts/`](../dts/README.md) is not needed. That workaround is written for the
upstream tree and cannot be built with ST's kernel.
