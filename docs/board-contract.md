# The board contract

Every directory under `boards/` follows the same contract, so that once you have built one board you
can build any other with the same few commands, and so that a new board is mostly a matter of filling
in a template. This page is both the rulebook for contributors and the answer to "why do all the
boards look alike?".

## 1. What a board directory is

A board directory is a **self-contained, from-source build** of the software a board needs to boot
Linux: the first-stage firmware, the bootloader, the kernel, a root filesystem, and whatever the
vendor's flashing model requires. It uses the vendor's or upstream's own source trees at **pinned
revisions**, builds them with a **pinned compiler**, and puts every artifact in one `build/deploy/`
folder. It does not use Yocto, Buildroot or any other build system. The point is to see every step.

Self-contained means you can copy one board directory out of this repository and it still works.
That is why each board carries its own copy of the small helper library in `scripts/lib/common.sh`.

## 2. Required layout

```text
boards/<soc>-<vendor-or-kit>/
├── README.md              the front door: diagram, quick start, status table, concept tour
├── build.sh               the single entry point (see §3)
├── config/
│   └── <board>.conf       every version pin and board constant, as  : "${VAR:=default}"
├── scripts/
│   ├── lib/common.sh      logging, run/explain mode, git_checkout, fetch, toolchain, patches
│   └── <step>.sh          one script per build step, each also callable on its own
├── patches/<component>/   *.patch applied in name order to the pinned sources (may be empty)
├── custom/                where the reader's own additions go (device trees, configs, overlays)
└── docs/
    ├── README.md          the reading order
    ├── 01-…  NN-…         numbered chapters (§5)
    └── images/            *.svg (committed) and _src/*.py (the generators)
```

Generated files live under `build/` and are git-ignored. Nothing a build produces is committed.

## 3. The command line every board answers

| Command | Meaning |
| --- | --- |
| `./build.sh deps [--install]` | check (or apt-install) the host packages |
| `./build.sh info` | print every pinned version, URL and path that the build will use |
| `./build.sh all` | everything from sources to a flashable artifact in `build/deploy/` |
| `./build.sh <step> …` | one step: the names are board specific and listed in `--help` |
| `./build.sh flash …` | write the artifact to the board's medium, with guards |
| `./build.sh clean` / `distclean` | drop outputs / drop everything including downloads |
| `--dry-run` (`-n`) | **explain mode**: print every command with a sentence on why it exists, run nothing |
| `--verbose`, `--jobs N`, `--update`, `--yes`, `--help` | as in the i.MX 8M Plus board |

`--dry-run` is the most important line of the contract. A reader who does not want to wait for a
build can read `./build.sh --dry-run all | less -R` and get the whole recipe, in order, with the
reasoning. Every step must therefore go through `run`, `run_sh`, `run_cd` or `fetch` from
`common.sh` rather than calling tools silently.

## 4. Rules for the scripts

1. `set -Eeuo pipefail` through `strict_mode`; every step writes a log to `build/logs/`.
2. Every download has a pinned **sha256** (`fetch`), every git source a pinned **commit**
   (`git_checkout`). A value of `…_REV=` (empty) means "follow the branch", and `--update` is the
   only way to move a checkout that already exists.
3. Nothing in the build needs root except the steps that cannot avoid it, and those say so. Image
   assembly is rootless wherever the format allows it (`fakeroot`, `mke2fs -d`).
4. `flash` refuses system disks, shows what it is about to overwrite and asks first.
5. Configuration is overridable per run from the environment, or persistently from
   `config/local.conf` (git-ignored). Scripts never edit the config file.
6. The scripts must pass `shellcheck -x`, and every step must complete in `--dry-run` on a plain
   Ubuntu 24.04 host. CI checks both.
7. No credentials, no board-specific secrets, no personal paths. A default password is allowed only
   when the docs say it is a bench default.

## 5. Required documentation

Every board ships these chapters, in this order, because the order is the order of the boot:

| # | Chapter | Answers |
| --- | --- | --- |
| 01 | Boot flow | What runs from power-on to a login prompt, in which privilege level, loaded by whom? |
| 02 | Host setup | What do I need on my PC, and how do I check it? |
| 03 | Bootloader (and firmware) | How is the first-stage firmware and the bootloader built, and what do they do? |
| 04 | Kernel | How is the kernel built, which device tree is used, how do I change it? |
| 05 | Root filesystem | What is in `/`, how is it built, how do I swap it? |
| 06 | Image or flash package | How is the final artifact laid out, byte for byte? |
| 07 | Flashing and booting | How do I get it onto the board, which switch or jumper, which serial port? |
| 08 | Customizing | Where does each kind of change go (patch, config fragment, device tree, rootfs hook)? |
| 09 | Troubleshooting | The failures that actually happen, with the symptom first. |
| 10 | Versions | Where each pin came from, and how to move to a newer release. |

A board may add more (the i.MX 8M Plus board has chapters on using the board, a board tour and its
secure world). Each README opens with a **status table** that says, per capability, what has been
verified and how: *built in CI*, *built in a container*, *booted on hardware*. Never claim more than
was done.

## 6. Required diagrams

Diagrams are SVG, drawn by a small Python generator (`docs/images/_src/kit.py`), in one dark theme with
one fixed colour per role, so a reader recognises a bootloader or a secure-world component at a glance
across boards:

| Colour | Role |
| --- | --- |
| rose | secure world: first-stage firmware that owns the highest privilege, secure monitor, TEE |
| teal | normal world: Linux and applications |
| blue | boot stages: ROM-loaded loaders, bootloader |
| amber | firmware blobs and image assembly |
| violet | device trees and the root filesystem |
| slate | hardware |
| dashed outline | optional, not part of the default build |

Every board has at least: **the boot chain**, **the build pipeline** (sources → artifact), **the storage
layout** (what is at which offset or partition), and **the source map** (which files to open to
understand each stage). Each diagram has an `aria-label`, is linked from the chapter that explains it,
and is listed in `docs/images/README.md`.

## 7. Adding a board

1. Pick a name: `<soc>-<kit>` in lower case, for example `rk3588-orangepi5`.
2. Copy the nearest existing board that has the same *flashing model* (SD-card image, or vendor flash
   tool over USB) and rename what changes. Keep `scripts/lib/common.sh` unless you must extend it.
3. Pin your sources, then make `./build.sh --dry-run all` read well before you make `all` work.
4. Write the chapters in §5 as you go, not afterwards. Draw the four diagrams in §6.
5. Add the board to the table in the root `README.md` and to `.github/workflows/ci.yml`.
6. State the verification level honestly in the board's status table.
