# Diagrams

All diagrams are SVG, so they render sharply on GitHub and in any browser, and their text is searchable.
They share one dark theme and one role palette (the same as the other boards of this repository):

| Colour | Means |
| --- | --- |
| rose | secure world: OP-TEE, `smc` |
| teal | normal world: Linux, applications |
| blue | boot stages: BL2, U-Boot |
| amber | firmware blobs, image assembly (here: the environment partition, differences in the comparison) |
| violet | device trees, the root filesystem |
| slate | hardware |
| dashed outline | optional / not part of the default build / absent on this chip |

| File | Shows | Used in |
| --- | --- | --- |
| `boot-chain.svg` | every boot stage: mode, address, job, source, what stays resident | README, 01 |
| `build-pipeline.svg` | what `./build.sh all` does, sources → SD card image | README, 08 |
| `sd-layout.svg` | the GPT partitions, who reads each, what is in the rootfs | README, 06, 07 |
| `fip-anatomy.svg` | what is inside `fip.bin`, with the real offsets and sizes | README, 03 |
| `memory-map.svg` | SYSRAM and DDR as the boot chain uses them | 01 |
| `uboot-bootflow.svg` | U-Boot's distro-boot decision flow with this board's values | 01, 03 |
| `scmi-flow.svg` | a regulator request from Linux to OP-TEE and back | README, 11 |
| `source-map.svg` | the source files that run at boot, in order, with real paths | README |
| `mp1-vs-mp2.svg` | this board against the 64-bit STM32MP257F-DK | README, 14 |

Every diagram has a `<name>.steps.json` walkthrough (see `docs/authoring-diagrams.md` at the top of the
repository); `python3 tools/check-steps.py boards/stm32mp1-dk2/docs/images/*.steps.json` checks that each
anchor exists in its SVG.

## Editing

Every SVG is generated; edit the Python and run it in `docs/images/_src/`:

```bash
cd docs/images/_src && ./make-images.sh      # runs every generator, rewrites ../*.svg
```

They all use the helpers in `_src/kit.py`. Icons are in `_src/icons/`.
Preview: open the `.svg` in a browser, or `rsvg-convert -w 1400 file.svg -o file.png`.
Every path and address in a diagram was read from the pinned source trees (`./build.sh info`) or from the
build described in `docs/10-versions.md`.

## Credits

- Icons: [Lucide](https://lucide.dev), ISC License, © Lucide Contributors; the Linux mark from
  [Simple Icons](https://simpleicons.org), CC0 1.0. The trademarks belong to their owners and are used only to
  identify the software.
