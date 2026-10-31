# Source patches

`*.patch` files here are applied in name order, once each, with `patch -p1` from `Linux_for_Tegra/source/` by
`./build.sh kernel`. Paths inside a patch are relative to that directory, for example
`kernel/kernel-jammy-src/drivers/…`, `nvidia-oot/drivers/…` or `hardware/nvidia/t23x/nv-public/nv-platform/…`.

An example that changes the device tree is in `../../custom/examples/0001-dts-add-primer-build-property.patch`.
See [docs/04 §5](../../docs/04-kernel.md#5-patches). Remove a patch with `./build.sh -u kernel`.
