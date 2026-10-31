# custom/dts/

Drop your own `*.dts` / `*.dtsi` files here. They are copied into
`arch/arm64/boot/dts/st/` of the kernel before it is built, and every `*.dts` is built into a `.dtb` that
ends up in `/boot` on the SD card. You can `#include` any ST file, for example
`#include "stm32mp257f-dk.dts"`.

To boot your tree, put it **first** in `KERNEL_DTBS` (`config/local.conf`); `scripts/image.sh` writes the
first entry into `extlinux.conf`:

```bash
KERNEL_DTBS="st/my-board.dtb st/stm32mp257f-dk.dtb"
```

## What is here

`stm32mp257f-dk-primer.dts` is the board's stock tree with the SD card's supplies replaced by fixed
regulators. It is the default boot tree, for the reason written at the top of the file and explained in
[docs/09](../../docs/09-troubleshooting.md#linux-never-finds-the-root-filesystem). Delete it (and
`KERNEL_DTBS`' first entry) if your OP-TEE implements SCMI voltage domains.

See `docs/08-customizing.md`.

This directory is for the mainline stack. ST's stack (`-s st`) has its own, [`../dts-st/`](../dts-st/README.md): the file
here includes the upstream tree and does not build against ST's kernel.
