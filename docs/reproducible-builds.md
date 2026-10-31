# Reproducible builds: where the boards stand and what to change

A build is **reproducible** when the same inputs give the same bytes: build the same commit twice, on two
machines, and the images have the same sha256. That makes a checksum mean "this is what that commit builds",
lets a reviewer rebuild a release and compare, and makes a bad build easy to spot.

**Status: none of the images is bit-for-bit reproducible today.** The *inputs* are pinned; the *build* still lets
the clock, random numbers and the live Debian archive into the output. This page lists both sides, what was
measured, and the changes each board needs. The images workflow can measure progress for the cheap parts
(boot firmware and boot loader) with its `reproducibility_check` input.

## What is pinned today

| Input | How it is pinned |
| --- | --- |
| Source repositories (U-Boot, TF-A, OP-TEE, Linux for i.MX) | a git commit id per component (`…_REV`), shown by `./build.sh info` and recorded in every release's `manifest.json` |
| Downloads (compilers, firmware archives, kernel tarballs, the Debian keyring, the Alpine minirootfs, NVIDIA's archives) | a sha256 checked by `fetch` |
| Compilers | Arm GNU Toolchain 14.3.rel1 (i.MX, STM32MP2) and NVIDIA's Bootlin-based GCC 11.3 (Jetson), by sha256 |
| Kernel configuration | defconfig plus the fragments in `config/kernel/`, and a check of the options the boot path needs |
| Tool versions | the image tool versions are recorded in `manifest.json` (`xz`, `mke2fs`, `sfdisk`, `mmdebstrap`, …) |
| Compression of the release assets | `xz -T1 -6`: one thread and a fixed level, because the xz manual says the single-threaded and multi-threaded encoders produce different output (and that output may differ between xz versions) |

## What is not pinned

| Source of difference | Where it comes from | Checked |
| --- | --- | --- |
| **Debian archive state** | the root filesystem is bootstrapped from `deb.debian.org/debian` (suites `trixie`, `trixie-updates`) and `security.debian.org` as they are on the build day | by reading `scripts/rootfs.sh` |
| **Build timestamps** | none of the scripts sets `SOURCE_DATE_EPOCH`, `KBUILD_BUILD_TIMESTAMP`, `KBUILD_BUILD_USER` or `KBUILD_BUILD_HOST` (a search of both SD-card boards found only `LOCALVERSION`) | by search |
| **ext4 identity** | `mke2fs -d` is called without `-U` and without `-E hash_seed=`, and without a fixed time | **measured** (see below) |
| **Disk identifiers** | the i.MX image uses an MBR partition table written by `sfdisk` without a `label-id`, so the disk identifier is random; the STM32MP2 script already fixes the GPT disk GUID and the partition UUID | by reading `scripts/image.sh` |
| **Tar ordering and times** | the Alpine rootfs tarball is made with `tar -cpf` on a directory (order and mtimes are whatever the filesystem gives) | by reading `scripts/rootfs.sh` |
| **Password hashes** | `password_hash` produces a SHA-512 hash with a fresh random salt for every build (the bench default passwords) | by reading `scripts/rootfs.sh` |
| **Boot loader banners** | U-Boot and TF-A print their build date; TF-A uses the compiler's `__DATE__`/`__TIME__` unless told otherwise | from their makefiles |
| **File names** | the images are named with `$(date +%Y%m%d-%H%M)` (the release step renames them to stable names, so this does not change the bytes) | by reading `scripts/image.sh` |
| **Absolute paths** | debug information and `__FILE__` carry the build directory, which is inside the board directory | kernel documentation |

## What was measured here

On Ubuntu 24.04 (arm64 container; `e2fsprogs` 1.47.0, which is what a 24.04 runner has), `mke2fs -t ext4 -d <tree>`
run twice on the same tree with the same file times:

| Options | Two runs identical? |
| --- | --- |
| none | no |
| `E2FSPROGS_FAKE_TIME=1700000000` | no (UUID and hash seed still random) |
| `SOURCE_DATE_EPOCH=1700000000` | no (1.47.0 ignores it) |
| `E2FSPROGS_FAKE_TIME=1700000000 -U <uuid> -E hash_seed=<uuid>` | **yes** |

Also measured: `tar --sort=name --owner=0 --group=0 --numeric-owner --format=gnu --mtime=@N` gives the same
archive after the files' times were touched; `bmaptool create` gives the same `.bmap` twice; the `xz -T1 -6`
packing of the release assets is repeatable (same input, same xz).

And `mmdebstrap` 1.4.3 (`--mode=root --variant=essential --architectures=arm64`, suite `trixie`, mirror
`http://snapshot.debian.org/archive/debian/20260101T000000Z`, `Acquire::Check-Valid-Until "false"`) run twice with
`SOURCE_DATE_EPOCH=1700000000` produced **byte-identical tarballs** (same sha256). That is the Debian half of the
problem solved by two settings; the board's `minbase` variant plus its package list and customize hook were not run
under this test.

## What to change

Every item names where it is documented. Items marked *not run here* come from the documentation only.

### Everywhere: one clock

Set `SOURCE_DATE_EPOCH` once in `build.sh`, from the commit, unless the caller already set it, and export it:
`export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git -C "$TOP_DIR" log -1 --format=%ct)}`. The images workflow does
the same from the tagged commit. Everything below reads it.

### Kernel

The kernel documentation on reproducible builds ([kbuild/reproducible-builds](https://www.kernel.org/doc/html/latest/kbuild/reproducible-builds.html)) names:

- `KBUILD_BUILD_TIMESTAMP` (the time in `uname`, `/proc/version`, the embedded initramfs), set to the commit date
  (`date -u -d @$SOURCE_DATE_EPOCH`),
- `KBUILD_BUILD_USER` and `KBUILD_BUILD_HOST`, set to fixed strings (for example `primer` and `build`),
- `KCFLAGS` / `KAFLAGS` with `-fdebug-prefix-map=<build dir>=.` so absolute paths stay out of debug information,
- `CONFIG_MODULE_SIG_ALL` disabled (it signs modules with a key generated per build) or a persistent signing key,
- a fixed `CONFIG_BUILD_SALT`, and for `CONFIG_RANDSTRUCT` a pre-generated `scripts/basic/randstruct.seed`,
- `CONFIG_LOCALVERSION_AUTO` unset, because `scripts/setlocalversion` adds the git state to the release string
  (the i.MX fragment already does this).

Pass them to every `make` through the existing `kmake` helper, which already carries `LOCALVERSION`.

### U-Boot and TF-A

- **U-Boot** honours `SOURCE_DATE_EPOCH` (its makefile writes `U_BOOT_DATE`, `U_BOOT_TIME` from it; it needs GNU `date`, which
  Ubuntu has) and uses it for the FIT device-tree blob time. Exporting the variable is enough.
- **TF-A** takes `BUILD_MESSAGE_TIMESTAMP` from the command line; the default is the compiler's `__TIME__`/`__DATE__`.
  The value must be a C string pair, for example `BUILD_MESSAGE_TIMESTAMP='"00:00:00", "Jan 01 2026"'` derived from
  `SOURCE_DATE_EPOCH`.
- **OP-TEE:** no timestamp variable was found in its top-level makefiles; compare two builds before assuming.

### Debian root filesystem (`mmdebstrap`)

From the mmdebstrap manual:

- With `SOURCE_DATE_EPOCH` set, "the result will be reproducible across multiple runs with the same options and
  mirror content". "Same mirror content" is the point: bootstrap from a **snapshot**, not the live archive.
  The manual shows `--aptopt='APT::Snapshot "20210205T164900Z"'` to select a `snapshot.debian.org` timestamp
  and `--aptopt='Acquire::Check-Valid-Until "false"'`, which old snapshots need. Equivalent: use
  `deb http://snapshot.debian.org/archive/debian/<timestamp>/ trixie main` as the mirror line.
  Make the timestamp a pinned setting (`DEBIAN_SNAPSHOT=20260101T000000Z`) and move it deliberately.
  The security suite has snapshots too; drop `-updates` or give it the same timestamp.
- `--mode=unshare` and `--mode=root` give bit-identical tarballs, so the rootless mode is not a source of differences.
- mmdebstrap's cleanup step already removes `/var/log/dpkg.log`, `/var/log/apt/history.log` and empties
  `/etc/machine-id`. It does **not** normalise `/etc/resolv.conf` and `/etc/hostname`, which it copies from the host:
  overwrite both in the customize hook (`debian-customize.sh`).
- The tarball is POSIX pax with extended attributes. The manual says nothing about entry order; check two runs.
- Replace the random salt in `password_hash` with a fixed one, for example
  `openssl passwd -6 -salt primerbench "$TARGET_PASSWORD"`. A fixed salt is acceptable only because these are bench
  default passwords that the docs tell you to change.

### Alpine root filesystem

The minirootfs download is already pinned by sha256. Re-pack the staged tree deterministically:
`tar --sort=name --owner=0 --group=0 --numeric-owner --format=gnu --mtime=@$SOURCE_DATE_EPOCH -C "$stage" -cf "$out" .`
(measured above), and clamp the file times in `$stage` first (`find "$stage" -exec touch -h -d @$SOURCE_DATE_EPOCH {} +`).
Packages added with `apk` pull the live index; pin the Alpine release and check the package versions.

### Image assembly (`image.sh`)

- `mke2fs -d`: run with `E2FSPROGS_FAKE_TIME=$SOURCE_DATE_EPOCH` **and** `SOURCE_DATE_EPOCH` (e2fsprogs 1.47.1 and later
  read `SOURCE_DATE_EPOCH`; 1.47.0, the version on Ubuntu 24.04, only `E2FSPROGS_FAKE_TIME`; the second is a fallback in
  newer versions), a fixed `-U <uuid>` and `-E hash_seed=<uuid>`. Derive the UUID from the board and variant name
  (for example `uuidgen --sha1 --namespace @dns --name <board>-<variant>`) rather than writing it by hand.
  The files' own times come from the staged tree, which is why the tar extraction must keep mtimes (`tar -xp`) and the
  clamped times above matter.
- `sfdisk` (i.MX): add `label-id: 0x<8 hex digits>` to the script. STM32MP2 already sets `label-id` and the partition `uuid`.
- Do not put `$(date …)` in anything that ends up inside the image; the file name is not content, but a banner would be.
- `bmaptool create` is repeatable (measured), so the `.bmap` follows the image.

### Jetson kernel bundle

The kernel and NVIDIA's out-of-tree modules take the kernel variables above (`omake` must pass them too). The compiler is
pinned. The bundle is packed with sorted names, fixed owner and `--mtime=@$SOURCE_DATE_EPOCH` by `make-assets.sh`. NVIDIA's
driver package and root filesystem are downloaded as they are and are not part of any release.

### Checking

`tools/release/repro-check.sh` copies a board directory twice, builds the cheap parts in each copy with the same
`SOURCE_DATE_EPOCH`, and compares sha256. The images workflow runs it with `reproducibility_check` (boot firmware and
boot loader only: the kernel and the root filesystem are too slow for a routine check) and writes the result to the job
summary. For a difference, `diffoscope` shows where the bytes differ.

## Checklist per board

Tick these when the board's scripts do it. Each is one of the changes above.

### i.MX 8M Plus (Variscite)

- [ ] `build.sh` exports `SOURCE_DATE_EPOCH` (from the commit)
- [ ] `kmake`: `KBUILD_BUILD_TIMESTAMP`, `KBUILD_BUILD_USER`, `KBUILD_BUILD_HOST`, `KCFLAGS`/`KAFLAGS` prefix maps
- [ ] kernel config: `CONFIG_MODULE_SIG_ALL` off (or a stored key), `CONFIG_LOCALVERSION_AUTO` stays off
- [ ] U-Boot builds with `SOURCE_DATE_EPOCH` exported (check `U_BOOT_DATE` in the result)
- [ ] TF-A builds with `BUILD_MESSAGE_TIMESTAMP`
- [ ] `rootfs.sh` Debian: snapshot timestamp setting, `Acquire::Check-Valid-Until "false"`, resolv.conf/hostname fixed in the hook, fixed password salt
- [ ] `rootfs.sh` Alpine: sorted, clamped tar
- [ ] `image.sh`: `E2FSPROGS_FAKE_TIME`, `-U`, `-E hash_seed=`, `sfdisk` `label-id`
- [ ] the new uuu flow (once merged): deterministic zip of the boot image, root filesystem and scripts (`make-assets.sh` already sorts and clamps)

### STM32MP2 Discovery Kit

- [ ] `build.sh` exports `SOURCE_DATE_EPOCH`
- [ ] `kmake` kernel variables and config as above
- [ ] U-Boot `SOURCE_DATE_EPOCH`; TF-A `BUILD_MESSAGE_TIMESTAMP`; compare two OP-TEE builds
- [ ] `fiptool` output compared twice (the FIP carries no time as far as the documentation shows: confirm)
- [ ] `rootfs.sh`: same as the i.MX items
- [ ] `image.sh`: `mke2fs` options as above; the GPT disk GUID and partition UUID are already fixed

### STM32MP1 Discovery Kit (DK2) and Zynq-7000 Eclypse Z7 (when they land)

- [ ] copy the i.MX / STM32MP2 changes into the board when it is created, rather than retrofitting
- [ ] Zynq: the bitstream and first-stage files come from a vendor tool; record their sha256 and say so in the manifest

### Jetson Orin Nano

- [ ] `kmake` and `omake` pass the kernel variables; fixed `CONFIG_BUILD_SALT`
- [ ] nothing to do for NVIDIA's downloads (pinned by sha256); they are not redistributed
- [ ] the full flash package is out of scope for bit-for-bit comparison (it is generated and signed by NVIDIA's tools)
