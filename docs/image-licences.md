# What is inside the images: third-party components and licences

The scripts in this repository are original work; the images they build are not only that. An image is
the scripts' output **plus** firmware, a boot loader, a kernel and a distribution written by others. This page
lists what each published image contains and under which licence, so that someone who has to decide
about sharing an image can see what is in it. It states facts and where they come from. It draws **no legal
conclusion**; the open licence questions are at the end.

**Your own use.** Until the open questions at the end are settled, treat every image and bundle as **for your own
use only**: do not redistribute it, or a card written from it. Each release page repeats this.

## Components per image

| Component | In which images | Licence (where stated) | Source of the statement |
| --- | --- | --- | --- |
| NXP DDR training firmware (`lpddr4_pmu_train_*`), from NXP `firmware-imx` 8.32; also the SDMA, EASRC and XCVR firmware copied into `/lib/firmware/imx` | i.MX 8M Plus SD-card images, in `imx-boot.bin` and in the root filesystem | NXP software licence agreement ([LA_OPT_NXP_SW](https://www.nxp.com/docs/en/disclaimer/LA_OPT_NXP_SW.html)); the build asks you to accept it (`--accept-eula`) | [i.MX 8M Plus host setup](../boards/imx8mp-variscite/docs/02-host-setup.md#nxp-eula) |
| ST DDR PHY firmware (`stm32-ddr-phy-binary`) | STM32MP2 SD-card images, inside the FIP | ST's SLA0044 (`LICENSE.md` in that repository), not the BSD licence of TF-A | [STM32MP2 chapter 03](../boards/stm32mp2-dk/docs/03-firmware-and-uboot.md) |
| TF-A (BL2, BL31) | all SD-card images | BSD-3-Clause | board chapters 03 and the TF-A tree (`docs/license.rst`) |
| OP-TEE OS | STM32MP2 images | BSD-2-Clause | [STM32MP2 chapter 03](../boards/stm32mp2-dk/docs/03-firmware-and-uboot.md) |
| Arm SCP-firmware | STM32MP2 images | BSD-3-Clause | same |
| U-Boot | all SD-card images | GPL-2.0-or-later | same |
| Linux kernel | all images and the Jetson kernel bundle | GPL-2.0 | the kernel tree's `COPYING` |
| Variscite forks of U-Boot, TF-A and Linux (`uboot-imx`, `imx-atf`, `linux-imx`) | i.MX 8M Plus images | same licences as the upstream projects | pinned commits in `manifest.json` |
| Debian 13 ("trixie") packages | `*-debian` images | each package's own licence, in `/usr/share/doc/<package>/copyright` inside the image | Debian |
| Alpine 3.24 minirootfs | `*-alpine` images | each package's own licence, in the `L:` lines of `/lib/apk/db/installed` | Alpine |
| NVIDIA out-of-tree kernel modules and device trees, from NVIDIA's public sources | Jetson kernel bundle | the licence named in each source file's header | NVIDIA's `public_sources` archive |
| NVIDIA Jetson Linux driver package, flash tools, firmware, sample root filesystem | **not published** | NVIDIA Tegra Software License Agreement | [NVIDIA text for R36.4.3](https://developer.download.nvidia.com/embedded/L4T/r36_Release_v4.3/release/Tegra_Software_License_Agreement-Tegra-Linux.txt) |

The Debian images are bootstrapped from the archive components `main`, `contrib`, `non-free` and `non-free-firmware`
(the mirror lines in `scripts/rootfs.sh`); the packages installed are the ones listed in the board configuration
(`DEBIAN_PACKAGES`) and their dependencies. Which of those come from a non-free component is not recorded
anywhere yet; it can be read from the finished image: `dpkg-query -W -f='${Package} ${Section}\n'` shows a section such as
`non-free/utils` for a package from a non-free component.

## What the Jetson licence says, in short

From NVIDIA's Tegra Software License Agreement (the R36.4.3 text linked above): clause 1.1(d) allows distributing
the software for use with operating systems under an OSI-approved open-source licence, provided the binary files
are not modified (apart from uncompressing) and the agreement is given to each recipient; clause 2.1 limits use to
NVIDIA platforms; clause 2.3 forbids modifying or creating derivative works of software provided in binary form; and
clause 2.7 forbids selling, renting, sublicensing, distributing or transferring the software except as the
agreement grants. The sample root filesystem is modified by NVIDIA's own assembly scripts, and a flash package
contains generated, signed images. Whether either may be shared is a legal question; the only Jetson release asset
is therefore the kernel bundle, which contains nothing from NVIDIA's driver package.

## Source code for the GPL parts

Redistributing an image would bring source-code obligations for the GPL components (U-Boot and the
Linux kernel, and GPL packages in Debian or Alpine). What this repository gives you to meet them is traceability,
not a complete source offer:

- **Boot loaders and kernel:** every release's `manifest.json` lists the pinned source revisions (git commit ids,
  or the sha256 of the source archive) read from `./build.sh info` at build time. The i.MX 8M Plus sources are
  Variscite's public GitHub forks; the STM32MP2 kernel is a kernel.org tarball with a pinned sha256.
- **Debian:** source packages are in the Debian archive and, for any past date, on `snapshot.debian.org`. The image is
  built from the archive as it was on the build day; the exact package versions are in the image's
  `/var/lib/dpkg/status`. Pinning the build to a snapshot timestamp would make this exact
  ([reproducible builds](reproducible-builds.md)).
- **Alpine:** package sources are in Alpine's `aports` repository and package versions in `/lib/apk/db/installed`.

## Open licence questions

1. Who accepts the NXP software licence agreement when the workflow builds with `--accept-eula`, and does that
   acceptance cover the images the workflow publishes?
2. The terms of ST's SLA0044 for redistributing images that contain the DDR PHY firmware.
3. What the GPL requires if an image is redistributed (a written offer, or the source alongside) and
   whether the pinned commits plus snapshot archives are enough.
4. Whether packages from `contrib`, `non-free` or `non-free-firmware` end up in the Debian images, and under what terms.
5. The NVIDIA questions above, if a Jetson flash package is ever to be shared.
6. Trademark and branding of the vendors' names in file names and release pages.

Where this page and a licence text disagree, the licence text wins; please correct this page.
