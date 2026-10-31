# config/kernel/

Kernel configuration fragments: every `*.cfg` here is merged on top of `multi_v7_defconfig` when the kernel
`.config` is created (`scripts/kconfig/merge_config.sh`, then `make olddefconfig`).

```text
# example: config/kernel/10-debug.cfg
CONFIG_DYNAMIC_DEBUG=y
# CONFIG_DRM_NOUVEAU is not set
```

After changing fragments: `FORCE_CONFIG=1 ./build.sh kernel`

Everything the board needs to reach a login is already in `multi_v7_defconfig`; `docs/04-kernel.md` lists the
options, and `scripts/kernel.sh` checks that they are built in (`=y`, not `=m`: there is no initramfs).
