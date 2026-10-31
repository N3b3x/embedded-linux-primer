# 10 · Versions: what is pinned, where it came from, how to move

[Docs](README.md) › **10 · Versions**

## 1. The release

**Jetson Linux R36.4.3** is the release that ships in **JetPack 6.2** (the one that introduced the Orin Nano *Super* power
configuration). Its Developer Guide is published at
`https://docs.nvidia.com/jetson/archives/r36.4.3/DeveloperGuide/`, which is the document set every chapter here points to.

| Item | Value |
| --- | --- |
| Kernel | Linux **5.15.148-tegra** (source directory `kernel-jammy-src`) |
| Root filesystem | Ubuntu 22.04 (jammy) arm64 |
| Reference toolchain | Bootlin `aarch64--glibc--stable-2022.08-1`, GCC 11.3 (published in NVIDIA's R36.3 download folder; see below) |
| Host | Ubuntu 20.04 / 22.04 x86-64 (NVIDIA's Quick Start) |

## 2. The four files and their checksums

All values are in `config/jetson-orin-nano.conf`. They were **computed from NVIDIA's download servers on 2026-10-24**
(trust on first use) and compared with NVIDIA's own list where one exists.

| File | Size | NVIDIA's published SHA-1 |
| --- | --- | --- |
| `Jetson_Linux_r36.4.3_aarch64.tbz2` | 715,765,074 | `3eb3c5a19a417313383c3bce297e07274a237e36`: **matches** |
| `Tegra_Linux_Sample-Root-Filesystem_r36.4.3_aarch64.tbz2` | 1,827,877,026 | `0bdb4e655d48bdf7e7bd98d3b7b69480576bfd7e`: **matches** |
| `public_sources.tbz2` | 226,034,384 | not in `release_sha_hashes.txt`; the archive carries its own `public_sources_sha.txt` for the files inside |
| `aarch64--glibc--stable-2022.08-1.tar.bz2` | 140,109,376 | not listed |

The pinned sha256 values:

```text
949a44049c4ce6a8efdf572ea0820c874f6ee5d41ca3e4935b9f0e38d11873d2  Jetson_Linux_r36.4.3_aarch64.tbz2
67b85bae18a532dd2fd75399359ba10829c30c0e60d77231b614df39ab52156d  Tegra_Linux_Sample-Root-Filesystem_r36.4.3_aarch64.tbz2
2c177804679e3ed650dabec6fa958388579896f170570c6171a1b6c386669216  public_sources.tbz2
8af54f268c462b2d0737df8789b5e35db03a2d1ecbec90e20948f66f9244fcdd  aarch64--glibc--stable-2022.08-1.tar.bz2
```

NVIDIA publishes SHA-1 values in
`https://developer.nvidia.com/downloads/embedded/l4t/r36_release_v4.3/release/release_sha_hashes.txt`. SHA-1 is
weaker than sha256, so the scripts pin the sha256 and the comparison above was done once, by hand. Check yourself:

```bash
curl -sL https://developer.nvidia.com/downloads/embedded/l4t/r36_release_v4.3/release/release_sha_hashes.txt | grep -E "Jetson_Linux|Sample-Root"
sha1sum build/downloads/Jetson_Linux_r36.4.3_aarch64.tbz2 build/downloads/Tegra_Linux_Sample-Root-Filesystem_r36.4.3_aarch64.tbz2
```

URLs (all of them answer with a redirect to `developer.download.nvidia.com`):

```text
https://developer.nvidia.com/downloads/embedded/l4t/r36_release_v4.3/release/Jetson_Linux_r36.4.3_aarch64.tbz2
https://developer.nvidia.com/downloads/embedded/l4t/r36_release_v4.3/release/Tegra_Linux_Sample-Root-Filesystem_r36.4.3_aarch64.tbz2
https://developer.nvidia.com/downloads/embedded/l4t/r36_release_v4.3/sources/public_sources.tbz2
https://developer.nvidia.com/downloads/embedded/l4t/r36_release_v3.0/toolchain/aarch64--glibc--stable-2022.08-1.tar.bz2
```

The toolchain URL lives in the `r36_release_v3.0` folder (the R36.3 release); NVIDIA's R36.4.3 release page links to that
file.

## 3. Where each fact in this directory comes from

| Topic | NVIDIA source |
| --- | --- |
| Flash commands, recovery mode, board names, USB IDs | Developer Guide, *Quick Start* |
| Boot sequence, BootROM, PSC, MB1, MB2, UEFI | *Jetson AGX Orin, Orin NX and Orin Nano Boot Flow* |
| UEFI variables, boot order, boot mode, L4TLauncher | *UEFI* (under *Bootloader*) |
| Partition files and keywords | *Partition Configuration* |
| Initrd flashing options | `Linux_for_Tegra/tools/kernel_flash/README_initrd_flash.txt` and *Flashing Support* |
| Kernel build, module install, DTBs | *Kernel Customization* |
| Bootloader slots A/B | *Update and Redundancy* |
| Everything else (script behaviour) | the scripts themselves, in `Linux_for_Tegra/` |

## 4. Moving to another release

Another Jetson Linux R36 release (for example 36.x with a different third digit) usually only changes the file names and
checksums. A new major (R38 and beyond) changes the kernel, the toolchain and sometimes the tool layout, so budget for reading.

1. Open NVIDIA's release page for the new release (the *Jetson Linux* archive page) and copy the three release URLs.
2. Download them once and compute `sha256sum`; compare with NVIDIA's SHA-1 list (`release_sha_hashes.txt` in the same folder).
3. Edit `L4T_RELEASE`, `L4T_URL_BASE` and the three `*_SHA256` values (override in `config/local.conf` to try first).
4. Check the toolchain NVIDIA names in that release's *Jetson Linux Toolchain* page.
5. Run `./build.sh --dry-run all`, then check these before any real build:
   - the board file still exists: `ls Linux_for_Tegra/jetson-orin-nano-devkit-super.conf`;
   - NVIDIA's Quick Start for the new release: compare the flash command with `./build.sh info`;
   - the kernel source directory name (`KERNEL_SRC_DIR`, `kernel-jammy-src` in R36) and the `source/Makefile` target names;
   - `tools/l4t_flash_prerequisites.sh` package list against `HOST_PACKAGES` in `build.sh`;
   - the lsusb IDs in the *Quick Start*.
6. Update the table in the README and this chapter, and say how far you verified it.

## 5. Why not the newest?

R36.4.3 is a long-lived JetPack 6 release with the widest documentation, third-party coverage and a kernel (5.15) that most
Jetson drivers and tutorials target. A first-steps repository benefits from "everything you read online matches". The cost is an
older kernel than the SD-card boards of this repository use. The structure here (fetch → rootfs → kernel → image → flash) is the same
for later releases; only pins and the details above change.

Next: [11 · Recovery mode](11-recovery-and-usb-flash.md) · Prev: [09 · Troubleshooting](09-troubleshooting.md)
