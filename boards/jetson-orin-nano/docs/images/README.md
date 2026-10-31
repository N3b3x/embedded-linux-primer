# Diagrams

All diagrams are SVG, so they render sharply on GitHub and in any browser and their text is searchable. They are **generated** by
the Python files in `_src/` (shared theme and helpers in `_src/kit.py`), so they can be corrected in one place. The colours are the
repository-wide role palette ([board contract §6](../../../../docs/board-contract.md)):

| Colour | Means here |
| --- | --- |
| rose | secure world: the secure OS (OP-TEE), keys |
| teal | normal world: the Linux kernel and its modules |
| blue | boot stages: MB1, MB2, UEFI, L4TLauncher; the flash tool |
| amber | NVIDIA firmware binaries and download archives |
| violet | device trees and the root filesystem |
| slate | hardware: silicon, the board |
| dashed outline | optional: only needed to build your own kernel |

| File | Shows | Used in |
| --- | --- | --- |
| `boot-chain.svg` | the seven boot stages, the processor each runs on, where it is stored, who owns it; the other cores' firmware | README, 01 |
| `build-pipeline.svg` | the downloads, the three steps and the `Linux_for_Tegra` tree they fill, then the flash | README, 04 |
| `flash-flow.svg` | the USB flash as a sequence between PC and board, step by step | README, 07, 11 |
| `storage-layout.svg` | QSPI-NOR partitions and the root device's GPT, with sizes read from NVIDIA's XML files | README, 06 |
| `two-models.svg` | SD-card image model vs vendor-flash model, with a comparison table | README, 13 |
| `customize-map.svg` | where each kind of change goes, what to re-run, what gets rewritten | README, 08 |
| `source-map.svg` | the files that decide the boot, in boot order, with real paths | README, 15 |

## Editing

```bash
cd docs/images/_src
python3 boot_chain.py            # writes ../boot-chain.svg
python3 build_pipeline.py        # …and so on, one script per diagram
for f in *.py; do [ "$f" = kit.py ] || python3 "$f"; done      # all of them
```

- Edit the numbers and strings in the generator, not the SVG. Text colour is set with `style="fill:…"` by the helpers.
- Preview: open the `.svg` in a browser, or `rsvg-convert -w 1400 file.svg -o out.png`.
- Every fact in a diagram comes from NVIDIA's documentation or the R36.4.3 package. When you change one, change the chapter that cites it.

## Credits

Icons: [Lucide](https://lucide.dev) (ISC License, © Lucide Contributors); only the icons the generators use are kept in `_src/icons/`.
NVIDIA's name appears in text only, to identify the software.
