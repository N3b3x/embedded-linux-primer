# Diagrams

All diagrams are SVG, so they render sharply on GitHub and in any browser, and their text is searchable.
They share one dark theme and one role palette (the same as the other boards of this repository):

| Colour | Means |
| --- | --- |
| rose | secure world (not used on this board: the DDR controller is drawn in rose because the SPL must configure it before anything runs) |
| teal | normal world: Linux, applications |
| blue | boot stages: the U-Boot SPL and U-Boot |
| amber | firmware blobs and generated files: `ps7_init`, the PL and its bitstream |
| violet | device trees, the root filesystem |
| slate | hardware |
| dashed outline | optional / not part of the default build |

| File | Shows | Used in |
| --- | --- | --- |
| `boot-chain.svg` | the four boot stages: mode, address, job, source, what stays running | README, 01 |
| `build-pipeline.svg` | what `./build.sh all` does, sources → SD card image | README, 03, 08 |
| `sd-layout.svg` | the MBR disk, who reads each file of the FAT partition, `extlinux.conf`, the later-bitstream note | README, 06 |
| `bootbin-anatomy.svg` | the bytes of `BOOT.BIN` and the five tables `ps7_init` replays | 01, 03 |
| `source-map.svg` | the source files that run at boot, in order, with real paths | README |
| `ps-pl-map.svg` | the PS and PL halves of the Zynq-7000, the board wiring, how it differs from the other boards | 11 |
| `zmod-loading-order.svg` | where the Zmod ADC fits: the signal path and the order of work | 13 |

Each has a `<name>.steps.json` walkthrough for the site's diagram viewer. Check them with
`python3 tools/check-steps.py boards/zynq7000-eclypse-z7/docs/images/*.steps.json` from the repository root.

## Editing

Every SVG is generated; edit the Python and run it in `docs/images/_src/`:

```bash
cd docs/images/_src && ./make-images.sh      # runs every generator, rewrites ../*.svg
```

They all use the helpers in `_src/kit.py`. Icons are in `_src/icons/`.
Preview: open the `.svg` in a browser, or `rsvg-convert -w 1400 file.svg -o file.png`.
Every path, address and size in a diagram was read from the pinned source trees or from a build of this board
(`./build.sh info`).

## Credits

- Icons: [Lucide](https://lucide.dev), ISC License, © Lucide Contributors; the Linux mark from
  [Simple Icons](https://simpleicons.org), CC0 1.0. The trademarks belong to their owners and are used only to
  identify the software.
