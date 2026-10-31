# custom/

Your own additions, kept out of `build/` so `./build.sh clean` never deletes them.

| Path | Used by | What goes here |
| --- | --- | --- |
| `examples/` | you | ready-to-copy samples: a kernel config fragment (`psi.cfg`) and a device tree patch. **Not applied by default** |
| `boards/*.conf` | `./build.sh image` | your own board specification, copied next to NVIDIA's `Linux_for_Tegra/*.conf` ([docs/08 §6](../docs/08-customizing.md)) |
| `BCT/*` | `./build.sh image` | your own boot configuration table files, copied to `bootloader/generic/BCT/` |

Kernel config fragments belong in `config/kernel/`, source patches in `patches/source/`.
