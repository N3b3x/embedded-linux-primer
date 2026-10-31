# Third-party notices

This repository contains scripts and documentation only. The software it builds is downloaded by
the scripts from its upstream projects and is covered by its own licences; nothing from those
projects is stored here. The few third-party assets that *are* stored in this repository, or
bundled in the documentation site built from it, are listed below.

## Icons in the diagrams

The SVG diagrams embed small icons, copied into `docs/images/_src/icons/` of the repository and of
each board.

### Lucide

Most icons come from [Lucide](https://lucide.dev), released under the ISC licence.

> Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as part of Feather (MIT).
> All other copyright (c) for Lucide are held by Lucide Contributors 2022.
>
> Permission to use, copy, modify, and/or distribute this software for any purpose with or without
> fee is hereby granted, provided that the above copyright notice and this permission notice appear
> in all copies.
>
> THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
> SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
> AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
> WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
> NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
> OF THIS SOFTWARE.

### Simple Icons

The Linux, Debian and Alpine Linux marks come from [Simple Icons](https://simpleicons.org)
(CC0 1.0 Universal). The trademarks belong to their owners and are used only to identify the
software.

## Files fetched at build time, not stored here

The build scripts download these; they are not part of this repository and stay under their own terms:

- **NXP `firmware-imx`** (DDR training firmware for the i.MX 8M Plus), under NXP's software licence agreement,
  accepted with `--accept-eula`.
- **ST's DDR PHY firmware** for the STM32MP1 and MP2 (`stm32-ddr-phy-binary`), under ST's licence.
- **Digilent's Eclypse Z7 hardware description** (`system.hdf` from the Eclypse-Z7-OS repository), from which the
  Zynq board's `ps7_init` source is generated. The generated source carries a GPL-2.0-or-later header; the
  Digilent repository has no top-level licence file, so the file is downloaded rather than committed.
- **NVIDIA Jetson Linux** (driver package, sample root filesystem, public sources), under NVIDIA's licence,
  accepted with `--accept-license`.
- **Debian and Alpine packages** in the root filesystems, each under its own licence.

[Image licences](docs/image-licences.md) lists what each ready-built image contains.

## Documentation site tooling

The site is built with [MkDocs](https://www.mkdocs.org) (BSD-2-Clause),
[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) (MIT),
[PyMdown Extensions](https://facelessuser.github.io/pymdown-extensions/) (MIT) and
[mkdocs-minify-plugin](https://github.com/byrnereese/mkdocs-minify-plugin) (MIT). They are installed
at build time from `requirements-docs.txt`; the generated site contains the theme's own CSS, JavaScript
and icon sets, which carry their licences in their source files.
