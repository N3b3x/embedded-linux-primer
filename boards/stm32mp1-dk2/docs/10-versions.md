# 10 · Versions: what is pinned, why, and how to move

Every version lives in [`config/stm32mp157f-dk2.conf`](../config/stm32mp157f-dk2.conf). This board uses
**upstream releases**, not a vendor fork. That is a deliberate choice for a *first-steps* board: the sources
are the ones every tutorial and mailing list talks about, and each project's own documentation applies.
The price is that the pieces were never tested *together* by one vendor; see
[11](11-secure-world-and-scmi.md#which-boot-path-and-why-the-decision).

## The pins

Current when the board was written (October 2026). Each one is a commit **and** a tag/version; the commit is
what is checked out, the tag is what a human reads.

| Part | Version | Pin | Where it came from |
| --- | --- | --- | --- |
| TF-A | v2.15.0 | commit `da738d5e…` | `git ls-remote --tags https://review.trustedfirmware.org/TF-A/trusted-firmware-a`: the newest release tag; its `docs/plat/st/stm32mp1.rst` and `stm32mpus.rst` are the build recipe followed here |
| OP-TEE OS | 4.11.0 | commit `f54190f2…` | newest tag of `github.com/OP-TEE/optee_os`; has `PLATFORM=stm32mp1` and `core/arch/arm/dts/stm32mp157c-dk2-scmi.dts` (no `stm32mp157f-dk2.dts`) |
| U-Boot | v2026.07 | commit `ece349ad…` | a release with `stm32mp15_defconfig`, `arch/arm/dts/stm32mp157c-dk2-scmi-u-boot.dtsi` and an upstream copy of the F-DK2 tree. `v2026.10` exists (tag object `a58e2b7a…`, commit `5508406…`) and has not been tried; at `v2026.10` and `master` there is still no `stm32mp157f-dk2-u-boot.dtsi` |
| Linux | 6.18.58 | sha256 `069b19f9…` | newest 6.18 stable (a long-term series); has `arch/arm/boot/dts/st/stm32mp157f-dk2.dts` |
| Arm GNU Toolchain | 14.3.rel1 | four sha256 values | `arm-none-eabi` and `arm-none-linux-gnueabihf` for x86-64 and ARM64 hosts (URLs checked with `curl -I`, sums from Arm's `.sha256asc` files) |
| Debian | trixie (13), `armhf` | `debian-archive-keyring` 2025.1, sha256 `9ea7778e…` | the stable release at the time |
| Alpine | 3.24.2, `armv7` | `.sha256` fetched next to the file | |

The full 40-character commits are in the config file. TF-A's tag `v2.15.0` is an annotated tag, so
`git ls-remote` shows two lines for it: the tag object and, with `^{}`, the commit. The config pins the
commit.

## Why these versions go together

* The **TF-A STM32MP1 recipe** (`docs/plat/st/stm32mp1.rst` in its own tree) names the three other
  components and the exact make arguments: OP-TEE with `PLATFORM=stm32mp1`, U-Boot with a `stm32mp15_*`
  defconfig, BL2 with `ARCH=aarch32 ARM_ARCH_MAJOR=7`. (That page still names `stm32mp15_trusted_defconfig`
  and the EV1 trees; for FIP boot, U-Boot's own `doc/board/st/stm32mp1.rst` recommends `stm32mp15_defconfig`,
  which is what this board uses.)
* The **board's device trees** exist in all four projects at these versions, under *different* names: TF-A
  `fdts/stm32mp157f-dk2.dts`, OP-TEE `core/arch/arm/dts/stm32mp157c-dk2-scmi.dts`, U-Boot
  `dts/upstream/src/arm/st/stm32mp157c-dk2-scmi.dts` (the F tree has no `-u-boot.dtsi`), Linux
  `arch/arm/boot/dts/st/stm32mp157f-dk2.dts`. The check that the file you need exists is the first thing to
  do before moving any version; and the **SCMI** variants must agree across OP-TEE, U-Boot and Linux.
* The **toolchain** is what ARM documents for TF-A (`arm-none-eabi-`); one Arm release covers both the bare-metal and the
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
curl -sL https://developer.arm.com/-/media/Files/downloads/gnu/14.3.rel1/binrel/arm-gnu-toolchain-14.3.rel1-x86_64-arm-none-eabi.tar.xz.sha256asc
```

Then set the new values for one run to try them, for example:

```bash
UBOOT_BRANCH=v2026.10 UBOOT_REV= ./build.sh firmware uboot
```

An empty `*_REV` means "follow the tag" (no commit pin). When it works, put the tag **and** the commit in the
config file.

### A checklist before you bump

1. Does the board's device tree still exist in every project at the new version? (`ls` it.)
2. Read the TF-A `docs/plat/st/stm32mp1.rst` of the new version: did the make arguments change?
3. OP-TEE: does `core/arch/arm/plat-stm32mp1/conf.mk` still force `CFG_SCMI_MSG_VOLTAGE_DOMAIN`, and is there
   by now an F-DK2 tree (`stm32mp157f-dk2.dts`) you should use instead of the C-DK2 SCMI one?
4. U-Boot: do `bootcmd_stm32mp` and `u-boot,mmc-env-partition` still behave as described in
   [03](03-firmware-and-uboot.md)? Has U-Boot grown a `stm32mp157f-dk2-u-boot.dtsi` (then switch `UBOOT_DEVICE_TREE`)?
5. Linux: do the required options (the table in [04](04-kernel.md)) survive in the new `defconfig`? The
   script stops at configuration time if one is missing.

## Plan B: ST's own tested set

ST publishes the combination it tests and ships in its Yocto distribution (OpenSTLinux), on its own
branches of the same projects. The release pinned by ST's `meta-st-stm32mp` (`wrynose_v26.02.18`, which
carries the tags below) is:

| Part | ST's tag |
| --- | --- |
| Linux | `v6.6-stm32mp-r3` (`github.com/STMicroelectronics/linux`) |
| U-Boot | `v2023.10-stm32mp-r3` (`github.com/STMicroelectronics/u-boot`) |
| TF-A | `v2.10-stm32mp-r3` (`github.com/STMicroelectronics/arm-trusted-firmware`) |
| OP-TEE | `4.0.0-stm32mp-r3` (`github.com/STMicroelectronics/optee_os`) |

ST's Yocto layer lists this very kit as the example machine `stm32mp15-disco` ("STM32MP157F-DK2 board ONLY with
Optee boot and SDcard support") with the boot scheme `opteemin` (a minimal OP-TEE with the trusted
applications compiled out) by default, and ships example partition tables
(`files/wic/sdcard-stm32mp157f-dk2-optee-example.wks.in`: `fsbl1`, `fsbl2`, `metadata1`, `metadata2`, `fip-a`,
`fip-b`, `u-boot-env`, `bootfs`, `rootfs`, `userfs`). Its device trees for the F-DK2 are SCMI trees too. A
bench-proven configuration of the kit (the same ST layer, with the full-OP-TEE scheme `optee`) booted from
the microSD card with `stm32mp157f-dk2.dtb` and `console=ttySTM0,115200 earlycon`, which is why this board
copies the console, DTB name, GPT partition names (`fsbl1`, `fsbl2`, `fip`, `u-boot-env`) and type GUIDs
(`8DA63339-…` for the first-stage and environment partitions, `19D5DF83-…` for the FIP). **This repository's
scripts do not build ST's stack**: the make arguments and device-tree names differ in places, and it carries a
6.6 kernel instead of 6.18. The tags are listed here because they are the fallback if the all-upstream stack
gives you trouble ([09](09-troubleshooting.md#linux-never-finds-the-root-filesystem)), and because a vendor's
`ls-remote` is the quickest way to learn what ST currently considers consistent.

## Reproducibility notes

* Sources are fetched as shallow single commits (`git fetch --depth 1 <sha>`), so a rebuild a year from now
  gets the same bytes, as long as the servers keep serving that commit.
* The firmware is **not** bit-for-bit reproducible: build paths and timestamps end up in some outputs.
  Two builds in different directories can therefore differ by a few bytes (seen on the 64-bit sibling; not
  measured for this board).
* `./build.sh info` prints all of the above for the build you are about to run.
