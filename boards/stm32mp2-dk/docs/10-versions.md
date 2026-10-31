# 10 · Versions: what is pinned, why, and how to move

Every version lives in [`config/stm32mp257f-dk.conf`](../config/stm32mp257f-dk.conf). By default this board uses
**upstream releases**, not a vendor fork. That is a deliberate choice for a *first-steps* board: the sources
are the ones every tutorial and mailing list talks about, and each project's own documentation applies.
The price is that the pieces were never tested *together* by one vendor; see
[11](11-secure-world-and-scmi.md#what-this-repository-had-to-work-around). ST's own tested set is a second,
selectable stack with its pins in [`config/stack-st.conf`](../config/stack-st.conf): see
[Plan B](#plan-b-sts-own-tested-set-implemented-as-stackst) below.

## The pins

Current when the board was written (October 2026). Each one is a commit **and** a tag/version; the commit is
what is checked out, the tag is what a human reads.

| Part | Version | Pin | Where it came from |
| --- | --- | --- | --- |
| TF-A | v2.15.0 | commit `da738d5e…` | `git ls-remote --tags https://review.trustedfirmware.org/TF-A/trusted-firmware-a`: the newest release tag; its `docs/plat/st/stm32mp2.rst` is the build recipe followed here |
| DDR PHY firmware | v1.0-stm32mp (A2022.11) | commit `77447cf2…` | the only tag of ST's `stm32-ddr-phy-binary` |
| OP-TEE OS | 4.11.0 | commit `f54190f2…` | newest tag of `github.com/OP-TEE/optee_os`; has `PLATFORM=stm32mp2` and `core/arch/arm/dts/stm32mp257f-dk.dts` |
| Arm SCP-firmware | OP-TEE CI revision | commit `0d480804…` | the revision named in OP-TEE 4.11.0's `.github/workflows/ci.yml` for its `stm32mp2` builds |
| U-Boot | v2026.07 | commit `ece349ad…` | a release with `stm32mp25_defconfig` and `arch/arm/dts/stm32mp257f-dk-u-boot.dtsi`; v2026.10 appeared while this board was written and has not been tried |
| Linux | 6.18.58 | sha256 `069b19f9…` | newest 6.18 stable (a long-term series); has `st/stm32mp257f-dk.dts` |
| Arm GNU Toolchain | 14.3.rel1 | four sha256 values | `aarch64-none-elf` and `aarch64-none-linux-gnu` for x86-64 and ARM64 hosts |
| Debian | trixie (13) | `debian-archive-keyring` 2025.1, sha256 `9ea7778e…` | the stable release at the time |
| Alpine | 3.24.2 | `.sha256` fetched next to the file | |

The full 40-character commits are in the config file. TF-A's tag `v2.15.0` is an annotated tag, so
`git ls-remote` shows two lines for it: the tag object and, with `^{}`, the commit. The config pins the
commit.

## Why these versions go together

* The **TF-A STM32MP2 recipe** (`docs/plat/st/stm32mp2.rst` in its own tree) names the three other
  components and the exact make arguments: OP-TEE with `PLATFORM=stm32mp2`, U-Boot with
  `stm32mp25_defconfig`, the DDR firmware repository.
* The **board's device trees** exist in all four projects at these versions: TF-A `fdts/stm32mp257f-dk.dts`,
  OP-TEE `core/arch/arm/dts/stm32mp257f-dk.dts`, U-Boot `dts/upstream` (`st/stm32mp257f-dk`), Linux
  `arch/arm64/boot/dts/st/stm32mp257f-dk.dts`. The check that the file you need exists is the first thing to
  do before moving any version.
* The **toolchain** is what ARM documents for TF-A; one Arm release covers both the bare-metal and the
  Linux targets.

## How to find newer versions

```bash
# TF-A: newest release tags
git ls-remote --tags --refs https://review.trustedfirmware.org/TF-A/trusted-firmware-a | sed 's#.*refs/tags/##' | sort -V | tail
# U-Boot
git ls-remote --tags --refs https://github.com/u-boot/u-boot.git | sed 's#.*refs/tags/##' | grep -E '^v20[0-9]{2}\.[0-9]+$' | sort -V | tail
# OP-TEE
git ls-remote --tags --refs https://github.com/OP-TEE/optee_os.git | sed 's#.*refs/tags/##' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail
# Linux: newest in a series, and the tarball's checksum
curl -s https://cdn.kernel.org/pub/linux/kernel/v6.x/sha256sums.asc | grep -E 'linux-6\.18\.[0-9]+\.tar\.xz' | tail -3
# the commit behind an annotated tag (the ^{} line)
git ls-remote https://github.com/u-boot/u-boot.git 'refs/tags/v2026.07*'
# Arm toolchain checksums
curl -sL https://developer.arm.com/-/media/Files/downloads/gnu/14.3.rel1/binrel/arm-gnu-toolchain-14.3.rel1-x86_64-aarch64-none-elf.tar.xz.sha256asc
```

Then set the new values for one run to try them, for example:

```bash
UBOOT_BRANCH=v2026.10 UBOOT_REV= ./build.sh firmware uboot
```

An empty `*_REV` means "follow the tag" (no commit pin). When it works, put the tag **and** the commit in the
config file.

### A checklist before you bump

1. Does the board's device tree still exist in every project at the new version? (`ls` it.)
2. Read the TF-A `docs/plat/st/stm32mp2.rst` of the new version: did the make arguments change?
3. OP-TEE: does `core/arch/arm/plat-stm32mp2/conf.mk` still ask for `CFG_SCMI_SCPFW`, and does its CI
   name a different SCP-firmware revision?
4. U-Boot: do `bootcmd_stm32mp` and `u-boot,mmc-env-partition` still behave as described in
   [03](03-firmware-and-uboot.md)?
5. Linux: do the required options (the table in [04](04-kernel.md)) survive in the new `defconfig`? The
   script stops at configuration time if one is missing.

## Plan B: ST's own tested set, implemented as `STACK=st`

ST publishes the combination it tests and ships in its Yocto distribution (OpenSTLinux), on its own
branches of the same projects. The release pinned by ST's `meta-st-stm32mp` (`wrynose_v26.02.18`, "r3", which
carries the tags below) is built by `./build.sh -s st all` ([15](15-two-stacks.md)). Pins, all in
`config/stack-st.conf`:

| Part | ST's tag | Commit |
| --- | --- | --- |
| Linux | `v6.6-stm32mp-r3` (`github.com/STMicroelectronics/linux`) | `80d29586…` |
| U-Boot | `v2023.10-stm32mp-r3` (`github.com/STMicroelectronics/u-boot`) | `7fbc677b…` |
| TF-A | `v2.10-stm32mp-r3` (`github.com/STMicroelectronics/arm-trusted-firmware`) | `41575b25…` |
| OP-TEE | `4.0.0-stm32mp-r3` (`github.com/STMicroelectronics/optee_os`) | `afdfcb01…` |
| Device trees | branch `v6-stm32mp` (`github.com/STMicroelectronics/dt-stm32mp`), 2 commits after the tag `v6-stm32mp-r3` | `6e8d9fa1…` |
| Kernel fragments 03, 04 | `meta-st-stm32mp`, `recipes-kernel/linux/linux-stm32mp/6.6/`, at | `a5e5cef8…` (sha256 pinned) |
| DDR PHY firmware | the same as the mainline stack | `77447cf2…` |

Where the numbers came from: each tag is annotated, so `git ls-remote <repo> 'refs/tags/<tag>^{}'` gives the commit that
is pinned. The device-tree commit and the fragment locations are what ST's recipes
(`external-dt_6.0.bb`, `linux-stm32mp_6.6.bb`) name. Newer tags (`…-r3.1`) exist for all four projects; r3 is what the
recipes pin. ST's Yocto recipes ship Linux and U-Boot as a kernel.org/upstream tarball plus one patch: the tags are the
same trees, in one download. This stack, with ST's device trees (`stm32mp257f-dk-ca35tdcid-ostl`), is what a
bench-proven configuration booted on this kit.

To move it: change the tag **and** the commit in `config/stack-st.conf` (or, for one run,
`TFA_BRANCH=… TFA_REV=… ./build.sh -s st firmware tfa`), keep the four projects and the device-tree repository on the same
ST release, then check that the device tree still exists in `dt-stm32mp/stm32mp2/a35-td/`.

## Reproducibility notes

* Sources are fetched as shallow single commits (`git fetch --depth 1 <sha>`), so a rebuild a year from now
  gets the same bytes, as long as the servers keep serving that commit.
* The firmware is **not** bit-for-bit reproducible: build paths and timestamps end up in some outputs.
  `fip.bin` differs by a few bytes between two build directories even with identical inputs (1,999,368 bytes in
  `/build`, 1,999,328 in `/clean` in the runs recorded here); `tf-a-….stm32` was the same size in both.
* `./build.sh info` prints all of the above for the build you are about to run.
