# Kernel config fragments

Every `*.cfg` in this directory is merged on top of NVIDIA's `defconfig` by `./build.sh kernel`
(`scripts/kconfig/merge_config.sh`, then `make olddefconfig`). One option per line:

```text
CONFIG_PSI=y
CONFIG_SOME_DRIVER=m
# CONFIG_UNWANTED is not set
```

The `.config` is regenerated whenever a fragment is newer than it. A ready-made example is in
`../../custom/examples/psi.cfg`; copy it here to try it. See [docs/04](../../docs/04-kernel.md#3-kernel-configuration).
