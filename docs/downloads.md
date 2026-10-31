# Download and flash an image

Ready-built boot images, so that you can put a board to work without building anything first. They are
built on demand by the [images workflow](https://github.com/N3b3x/embedded-linux-primer/actions/workflows/images.yml)
from the scripts in this repository and published as GitHub Releases. Nothing is built on every push.

> **Read before you flash.** Only the i.MX 8M Plus images have been **booted on hardware**. The STM32MP2
> images were built and inspected in a container but never booted on a kit, and the Jetson kernel bundle was
> never flashed on a board. Each card below says which is which. The images contain third-party firmware under
> vendor licences: they are for **your own use**, not for redistribution ([licences](image-licences.md)).

## Latest builds

This list is written when the documentation site is built (after every release). Verified images come first;
previews, which were never booted on hardware, are in a separate section with a warning. Each card shows size,
checksum and what was verified.

<div id="dv-downloads"></div>

The list above is drawn by JavaScript; the table below works without it.

## What is available

Every publication makes **two releases** from one tag, so that the stable links only ever serve images that
someone has booted:

| Release | Contains | Kind |
| --- | --- | --- |
| `<tag>` (for example `v1.2.0`) | only images whose board and variant have `verified_on_hardware: true` in `tools/release/images.json` | normal release: `releases/latest/download/<file>` points here |
| `<tag>-preview` (for example `v1.2.0-preview`) | every image that is **not** verified, with a warning in its notes and a manifest that names the unverified board and variant and why | pre-release, created only when something unverified was built |

A board moves from the preview stream to the verified one when `verified_on_hardware` is set to `true` in
`images.json` after someone has booted it; `verified_note` holds only the hardware description (board revision and carrier).

File names carry **no version**, so a link such as `releases/latest/download/<file>` always points at the newest
verified release. The version is on the release page, in `manifest.json` and in `SHA256SUMS`. Sizes are
estimates until the first release is published.

### Verified: stable links

| Board | Image | Download | Size | Verified on hardware |
| --- | --- | --- | --- | --- |
| i.MX 8M Plus (Variscite) | SD card, Debian 13 | [`imx8mp-variscite-debian.img.xz`](https://github.com/N3b3x/embedded-linux-primer/releases/latest/download/imx8mp-variscite-debian.img.xz) | about 600 MB | **yes**: VAR-SOM-MX8M-PLUS on Symphony |
| i.MX 8M Plus (Variscite) | SD card, Alpine 3.24 | [`imx8mp-variscite-alpine.img.xz`](https://github.com/N3b3x/embedded-linux-primer/releases/latest/download/imx8mp-variscite-alpine.img.xz) | about 200 MB | **yes**: VAR-SOM-MX8M-PLUS on Symphony |

### Previews: NOT verified on hardware

These are published only in the `<tag>-preview` pre-release; the files have the same names as they will have once
verified, but no `latest/download` link serves them. Open the newest
[pre-release on the releases page](https://github.com/N3b3x/embedded-linux-primer/releases) or use
the cards above. They may not boot at all: use them next to a serial console.

| Board | Image | File | Size | Why it is a preview |
| --- | --- | --- | --- | --- |
| STM32MP257F-DK | SD card, Debian 13 | `stm32mp2-dk-debian.img.xz` | about 600 MB | built and inspected in a container, never booted on a kit |
| STM32MP257F-DK | SD card, Alpine 3.24 | `stm32mp2-dk-alpine.img.xz` | about 200 MB | same |
| Jetson Orin Nano | kernel bundle (Image, modules, device trees) | `jetson-orin-nano-kernel.tar.xz` | about 140 MB | kernel recipe built in a container, never flashed on a kit |

Every image has a companion `<name>.img.bmap` (optional, for `bmaptool`) and every release has its own `SHA256SUMS` and
`manifest.json` (board, commit, pinned source revisions, tool versions, checksums). Planned, not published yet:
the STM32MP157F-DK2 and Zynq-7000 Eclypse Z7 images (their entries in `images.json` are disabled until the boards are
checked) and a uuu bundle for the i.MX 8M Plus (see [uuu](#nxp-uuu-flash-the-emmc-over-usb)).

### Which links work

- The links work for **anyone who can see the repository**. In a browser that is logged in to GitHub the file
  downloads directly. `curl` and `wget` get a 404 for an internal or private repository because they carry no
  login: use the GitHub CLI instead, for example
  `gh release download --repo N3b3x/embedded-linux-primer --pattern 'imx8mp-variscite-alpine.img.*' --pattern SHA256SUMS`
  (without a tag it takes the latest release; `--dir` chooses the folder; for a preview give its tag, `v1.2.0-preview`).
- GitHub defines the **latest release** as the most recent release that is neither a draft nor a pre-release
  ([REST API: get the latest release](https://docs.github.com/en/rest/releases/releases)). That is why previews are a
  separate pre-release: they can never take over the stable links.
- Until a verified release exists (run the workflow with a tag; the i.MX 8M Plus images are the verified ones), the stable
  links return 404.
- Builds that were not published are **workflow artifacts** and expire after 14 days. The releases are the durable copy.

## Linux

1. Download the `.img.xz` and `SHA256SUMS` into one folder.
2. Check the download: `sha256sum -c SHA256SUMS --ignore-missing`.
3. Write it with the script of this repository. It is one standalone file; copy [`tools/flash-sd.sh`](../tools/flash-sd.sh)
   anywhere:

   ```bash
   tools/flash-sd.sh imx8mp-variscite-alpine.img.xz
   ```

   It checks the image against `SHA256SUMS` (found next to it), lists **only removable or USB disks**
   (`lsblk`), refuses any disk that has a filesystem mounted at `/` or another system path, shows model
   and size, and makes you type the device name. Then it unmounts the card, streams `xz -dc | dd`
   (or `bmaptool copy` when `bmaptool` is installed and the `.bmap` is next to the image), syncs and ejects.
   Options: `--list` (show candidate disks), `--dry-run`, `--verify` (read the card back and compare a sha256),
   `-d /dev/sdX` (skip the menu), `--no-bmap`.
   An SD card in a laptop's built-in reader (`/dev/mmcblk0`) is often reported as non-removable: a USB reader
   is the safe choice, or add `--allow-internal` (the disk holding `/` is still refused).

   Without the script:

   ```bash
   xz -dc imx8mp-variscite-alpine.img.xz | sudo dd of=/dev/sdX bs=4M conv=fsync status=progress
   # or, writing only the used blocks (package bmap-tools; it finds imx8mp-variscite-alpine.img.bmap by itself):
   sudo bmaptool copy imx8mp-variscite-alpine.img.xz /dev/sdX
   ```

   `bmaptool` skips blocks that are zero in the image. `flash-sd.sh` therefore clears the first 16 MiB of the card
   first, so a U-Boot environment saved by an earlier use cannot survive; if you run `bmaptool` yourself, do the
   same (`sudo dd if=/dev/zero of=/dev/sdX bs=1M count=16`).

## macOS

1. Install `xz` once: `brew install xz`.
2. Check the download: `grep imx8mp-variscite-alpine.img.xz SHA256SUMS | shasum -a 256 -c -`.
3. Write it:

   ```bash
   tools/flash-sd.sh imx8mp-variscite-alpine.img.xz
   ```

   The script lists only disks that `diskutil list external physical` reports, refuses internal disks and the
   disk that holds the running system, asks you to type the device name (`disk4`), runs `diskutil unmountDisk`,
   writes to the raw device `/dev/rdisk4`, syncs and runs `diskutil eject`.
   macOS `dd` shows no progress by itself: press Ctrl-T, or install `pv` and the script uses it.

   Without the script: `diskutil list external physical`, then
   `diskutil unmountDisk /dev/disk4`, `xz -dc image.img.xz | sudo dd of=/dev/rdisk4 bs=4m`, `diskutil eject /dev/disk4`.

## Windows

There is no PowerShell script. Use one of two graphical tools; both read the `.xz` file directly, so do not unpack it.

1. Check the download. In a Command Prompt, in the folder of the download:

   ```text
   certutil -hashfile imx8mp-variscite-alpine.img.xz SHA256
   ```

   and compare the printed value with the line for that file in `SHA256SUMS` (`certutil -hashfile` supports
   MD5, SHA1, SHA256, SHA384 and SHA512; Microsoft's `certutil` documentation).
2. Either **Raspberry Pi Imager**: *Choose OS*, then **Use custom**, pick the `.img.xz`; *Choose storage*, pick the
   SD card; *Write*. The Imager's source lists `.img`, `.zip`, `.gz`, `.xz`, `.zst` and `.wic` as image files.
3. Or **balenaEtcher**: *Flash from file*, pick the `.img.xz`, *Select target*, *Flash*. Etcher's source lists
   `xz` among its supported formats. Etcher runs on Windows 10 and later, macOS and most Linux distributions.

Neither tool uses the `.bmap`; it is only for `bmaptool` on Linux.

## After flashing: boot and console

1. Put the card in the board and set the **boot switch to SD**, with the board unpowered.
2. Connect the serial console (115200 baud) and power on.
3. Log in. These are bench defaults, change them on anything that is not a prototype.

| Board | Console | Login | Read next |
| --- | --- | --- | --- |
| i.MX 8M Plus | `ttymxc0` on DART, `ttymxc1` on VAR-SOM and VAR-SMARC | `root` / `variscite` | [flashing and first boot](../boards/imx8mp-variscite/docs/07-flashing-and-boot.md), [board README](../boards/imx8mp-variscite/README.md) |
| STM32MP257F-DK | the ST-LINK port, usually `/dev/ttyACM0` | `root` or `dev`, password `stm32mp2` | [flashing and booting](../boards/stm32mp2-dk/docs/07-flashing-and-booting.md), [board README](../boards/stm32mp2-dk/README.md) |

If an unverified image does not boot, the first thing to look at is the last line the serial console printed;
the board's *Troubleshooting* chapter lists the failures seen so far.

## NXP uuu: flash the eMMC over USB

The i.MX 8M Plus Boot ROM can take a boot loader over USB ("serial download" mode), which is how you write the
on-module eMMC or run the build from RAM without an SD card. NXP's tool for this is **uuu** (Universal Update Utility),
from the [mfgtools releases](https://github.com/nxp-imx/mfgtools/releases). The latest release at the time of
writing (1.5.243) publishes `uuu.exe` for Windows, `uuu` and `uuu-ubuntu20.04` for Linux x86-64, `uuu_aarch64`
and `uuu_armv7` for Arm Linux and `uuu_mac_arm` for macOS on Apple silicon, plus a `UUU.pdf` manual.

- **Windows:** the project's README says the firmware uses WCID to load the WinUSB driver automatically, that
  Windows 10 installs it without help, and that Windows 7 needs the WinUSB driver from [Zadig](https://zadig.akeo.ie/).
  Nothing else has to be installed.
- **Linux:** uuu talks to the USB device directly, so it needs permission: run it with `sudo`, or install a udev rule
  (the board's `./build.sh uuu udev` does that; the uuu README does not cover it).
- **macOS:** the README lists macOS (Catalina) as a platform but also marks it as not tested; expect to try it first.

The board's own flow is [16 · Booting from the eMMC, and flashing it over USB with uuu](../boards/imx8mp-variscite/docs/16-booting-from-emmc-with-uuu.md)
(`./build.sh uuu emmc` or `uuu boot`).

A prebuilt **uuu bundle** (a zip with the boot image, the root filesystem image, the `.uuu` script and a README) is
planned and defined in `tools/release/images.json`, but disabled until the board's uuu step is merged. Until then,
build it from the board directory.

## NVIDIA Jetson: why there is no image

A Jetson Orin Nano boots from firmware in the QSPI flash on the module; the SD card, NVMe or USB drive holds only
the operating system. NVIDIA's tools write both over USB with the board in recovery mode, so there is no
`sdcard.img` to download ([SD card vs vendor flash](../boards/jetson-orin-nano/docs/13-sd-card-vs-vendor-flash.md)).

**What NVIDIA's flash tools need.** NVIDIA's Quick Start for Jetson Linux R36.4.3 asks for "a separate Linux
(Ubuntu 22.04 or Ubuntu 20.04) host system", and its release notes give the flashing host as
Ubuntu x64 20.04 or 22.04. So the flash runs on an **Ubuntu x86-64** PC. The Jetson Linux developer guide does not
mention virtual machines or WSL for this flow. when a user asked on NVIDIA's developer forum whether SDK Manager
can flash from a VM, NVIDIA staff answered that it is not supported (November 2024). The flash also needs the board to re-enumerate on USB several times (first the recovery
device, later a USB Ethernet device), which breaks easily when USB is passed through to a VM
([host setup, chapter 02](../boards/jetson-orin-nano/docs/02-host-setup.md)). NVIDIA's separate SDK Manager documentation does describe a
Windows route through WSL2 (needs usbipd-win 4.3.0 or newer, and says flashing an external storage device is not
supported there); this repository's scripts do not use SDK Manager and refuse to run on anything but x86-64 Linux.
Plan on a real Ubuntu x86-64 machine.

**Why the full flash package is not published.** It contains NVIDIA's Jetson Linux driver package and a root
filesystem modified by NVIDIA's tools. NVIDIA's Tegra Software License Agreement allows distribution only in the
cases its clause 1.1 names (for example unmodified binaries, for use with an open-source operating system, with
the agreement passed on), limits use to NVIDIA platforms (clause 2.1) and otherwise forbids distributing the
software (clause 2.7). Whether a flash package built here falls under clause 1.1 is a question for legal, so it is
not published; it would also need 40 to 60 GB and `sudo`, which a standard runner cannot offer. Each person
downloads NVIDIA's files from NVIDIA with `./build.sh fetch`.

**What the kernel bundle is.** `jetson-orin-nano-kernel.tar.xz` holds only what is built from NVIDIA's public
sources: the arm64 `Image`, the device trees (`dtb/`), and the in-tree and NVIDIA out-of-tree modules
(`modules/lib/modules/<version>/`). Unpack it next to a `Linux_for_Tegra` tree you built with the board's scripts
(`./build.sh --accept-license fetch bsp` and `rootfs`), then apply it the way the board's `kernel install` step does
(`scripts/kernel.sh`). The same commands are in the bundle's `README.txt`:

```bash
L4T=boards/jetson-orin-nano/build/work/Linux_for_Tegra
sudo cp -a modules/lib/modules/* "$L4T/rootfs/lib/modules/"
sudo cp Image "$L4T/rootfs/boot/Image"
cp Image "$L4T/kernel/Image"
cp dtb/*.dtb "$L4T/kernel/dtb/"
(cd "$L4T" && sudo ./tools/l4t_update_initrd.sh)
```

Then continue with `./build.sh image` and `./build.sh flash`
([flashing and booting](../boards/jetson-orin-nano/docs/07-flashing-and-booting.md),
[recovery mode](../boards/jetson-orin-nano/docs/11-recovery-and-usb-flash.md)).
This application path repeats what the install step does; it has not been run on a board.

## For maintainers

- What is built and published is one JSON entry per board and variant: `tools/release/images.json`.
- Run the workflow by hand (*Actions*, *images*, *Run workflow*) or push a tag: `git tag v1.2.0 && git push origin v1.2.0`.
- Reproducibility status and what is missing: [reproducible builds](reproducible-builds.md).
