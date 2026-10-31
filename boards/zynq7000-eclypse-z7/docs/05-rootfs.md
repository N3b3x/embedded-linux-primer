# 05 · The root filesystem

What is in `/`, how it is built, and how to swap it. `./build.sh rootfs` produces **one** file,
`build/deploy/rootfs.tar`, which `scripts/image.sh` unpacks into the SD card's ext4 partition.

All three choices must be **32-bit ARMv7 with hard-float** (Debian calls it `armhf`, Alpine `armv7`). A 64-bit
(arm64/aarch64) root filesystem cannot run on this CPU at all.

| `-r` / `ROOTFS=` | What | Size | Needs |
| --- | --- | --- | --- |
| `debian` (default) | Debian 13 "trixie", `armhf`, built with `mmdebstrap`: systemd, apt, ssh, DHCP | 266 MiB tar, 314 MiB in the ext4 | `mmdebstrap`, **qemu-user** (on every PC, also ARM64), `arch-test`, and either `sudo` or `uidmap` |
| `alpine` | Alpine 3.24.2 `armv7` minirootfs + a serial login: busybox init | 5.5 MiB tar | nothing but `fakeroot`, no emulation |
| `/path/to/rootfs.tar[.gz\|.xz\|.zst\|.bz2]` | your own (Buildroot, Yocto, a vendor image) | – | must be 32-bit ARMv7 hard-float |

```bash
./build.sh rootfs                      # Debian
./build.sh -r alpine rootfs            # Alpine: the quickest way to test a new card
./build.sh -r /path/to/my-rootfs.tar.zst rootfs
```

`./build.sh all` reuses an existing `rootfs.tar`; pass `-r` or set `REBUILD_ROOTFS=1` to make a new one.

## Debian

`scripts/rootfs.sh` runs `mmdebstrap --architectures=armhf --variant=minbase` with the package list in
`DEBIAN_PACKAGES` (config file) plus `systemd-resolved`, and the Debian archive keyring downloaded with a pinned
sha256 (so it works on Ubuntu hosts that lack the trixie key). Everything that makes the bootstrap *this board's*
system is in `scripts/rootfs/debian-customize.sh`, read it, it is commented line by line:

| What | How |
| --- | --- |
| hostname | `eclypse-z7` (`TARGET_HOSTNAME`), also in `/etc/hosts` |
| `/etc/fstab` | `LABEL=rootfs /` ext4, and `LABEL=BOOT /boot/firmware` vfat with `nofail`: the FAT partition is visible on the running board, so you can replace the kernel from there |
| users | `root` and `dev` (sudo); the **password `zynq7000` is a bench default**: set `TARGET_PASSWORD` in `config/local.conf`. Only salted SHA-512 hashes go into the image, from a file deleted after the bootstrap |
| network | `systemd-networkd`, DHCP on every Ethernet port (`Name=e*`), `systemd-resolved` |
| ssh | host keys are removed from the image and generated on first start (a drop-in puts `ssh-keygen -A` before the unit's own `sshd -t`) |
| first boot | empty `/etc/machine-id`, so systemd makes a unique one |
| serial login | systemd starts `serial-getty@ttyPS0` because the kernel command line says `console=ttyPS0,115200` |

**Why qemu on an ARM64 PC.** `mmdebstrap` installs packages by running their maintainer scripts *inside* the new
root. They are 32-bit `armhf` programs. The CPUs of most 64-bit Arm machines (Apple silicon, Ampere, most
servers) have no 32-bit mode. So `qemu-user-static` and a registered `binfmt_misc` handler are required there
too: the script checks for one whose magic is "32-bit little-endian ARM ELF" and tells you what to install.
It took about 6 minutes in the container used for this board.

Rootless: `mmdebstrap --mode=unshare` (user namespaces, package `uidmap`) when your system allows it, `sudo`
otherwise. On Ubuntu 24.04, `sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0` re-enables the
rootless mode.

## Alpine

Download of `alpine-minirootfs-3.24.2-armv7.tar.gz` (its published `.sha256` is fetched and checked), then, inside
one `fakeroot` session: hostname, `fstab`, the root password hash, `securetty` for `ttyPS0`/`ttyPS1`, a `getty`
wrapper that reads the console from `/proc/cmdline` (`console-getty`), an `inittab` that mounts `/proc`, `/sys`,
`/dev/pts`, starts `syslogd`, `mdev` (hotplug), a coldplug script that loads the modules for the hardware found at
boot, and a login on the serial console. There is no `apk` network set-up: run `udhcpc -i end0` and
`apk add …` yourself, or extend `scripts/rootfs.sh`.

## Using your own tarball

Pass the path with `-r`. It is used as-is, with the kernel's modules and `/boot/config-*` added by `image.sh`. It
needs: `/sbin/init`; a login on `ttyPS0` at 115200; and, if it uses a different fstab, a root entry that does not
depend on the device name (the kernel was told `root=PARTUUID=5a796e71-02`).

## What `image.sh` adds to every rootfs

* `/lib/modules/6.18.58-custom/…` and `/boot/config-6.18.58-custom` from the kernel step (merged with
  `--keep-directory-symlink`: on Debian `/lib` is a symlink to `usr/lib`);
* nothing else. In particular, the kernel, the device tree and `extlinux.conf` are on the **FAT** partition, not in
  `/boot` ([06](06-sdcard-image.md)).

Next: [06 · The SD card image](06-sdcard-image.md).
