# config/kernel/

Kernel configuration fragments: every `*.cfg` here is merged on top of the arm64 `defconfig` when the
kernel `.config` is created (`scripts/kconfig/merge_config.sh`, then `make olddefconfig`). With `-s st` they are
merged after ST's four fragments, so they win; they apply to both stacks.

```text
# example: config/kernel/10-debug.cfg
CONFIG_DYNAMIC_DEBUG=y
```

`00-base.cfg` is the one shipped: it keeps `uname -r` predictable and switches the `etnaviv` GPU driver off
([docs/09](../../docs/09-troubleshooting.md#a-gpu-driver-takes-the-board-down)).

After changing fragments: `FORCE_CONFIG=1 ./build.sh kernel`

Everything the board needs to reach a login is already in the defconfig; `docs/04-kernel.md` lists the
options. Anything between the CPU and the root partition must be `=y`, not `=m`.
