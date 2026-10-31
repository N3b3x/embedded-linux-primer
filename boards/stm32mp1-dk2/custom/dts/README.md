# custom/dts/

Drop your own `*.dts` / `*.dtsi` files here. They are copied into
`arch/arm/boot/dts/st/` of the kernel before it is built, and every `*.dts` is built into a `.dtb` that
ends up in `/boot` on the SD card. You can `#include` any ST file, for example
`#include "stm32mp157f-dk2.dts"`.

To boot your tree, put it **first** in `KERNEL_DTBS` (`config/local.conf`); `scripts/image.sh` writes the
first entry into `extlinux.conf`:

```bash
KERNEL_DTBS="st/my-board.dtb st/stm32mp157f-dk2.dtb"
```

## What is here

Nothing, on purpose. The 64-bit STM32MP257F-DK needs a device-tree workaround for its SD card supply; this
board does not, because OP-TEE's STM32MP15 SCMI server serves voltage domains
([docs/11](../../docs/11-secure-world-and-scmi.md)). The stock `stm32mp157f-dk2.dtb` is booted.

See `docs/08-customizing.md`.
