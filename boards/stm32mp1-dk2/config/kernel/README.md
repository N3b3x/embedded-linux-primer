# config/kernel/

Kernel configuration fragments: every `*.cfg` here is merged on top of the 32-bit `multi_v7_defconfig` when
the kernel `.config` is created (`scripts/kconfig/merge_config.sh`, then `make olddefconfig`).
Do not use `stm32_defconfig`: it is for the Cortex-M microcontrollers.

```text
# example: config/kernel/10-debug.cfg
CONFIG_DYNAMIC_DEBUG=y
CONFIG_DRM_STM=y
```

After changing fragments: `FORCE_CONFIG=1 ./build.sh kernel`

Everything the board needs to reach a login is already in `multi_v7_defconfig`; `docs/04-kernel.md` lists the
options. Anything between the CPU and the root partition must be `=y`, not `=m`.
