# 05 · The root filesystem

The **root filesystem** is everything in `/`: the init program, a shell, libraries, `apt`, your
applications. The kernel is useless without one. This board builds it into one tarball,
`build/deploy/rootfs.tar`, which [`scripts/image.sh`](../scripts/image.sh) unpacks into the SD card's ext4
partition. You choose the contents with `-r`:

```bash
./build.sh rootfs                  # Debian trixie (default)         ~4 min, 310 MB tar
./build.sh -r alpine rootfs        # Alpine minirootfs, no root      seconds, 9 MB tar
./build.sh -r /path/to/my.tar.zst rootfs     # bring your own tarball (Buildroot, Yocto, …)
```

| | Debian trixie | Alpine 3.24 | your own tarball |
| --- | --- | --- | --- |
| what it is | a full distribution: systemd, apt, ssh, thousands of packages | BusyBox + musl, a toolbox | anything |
| good for | exploring the board, running real software | first bring-up, smoke tests, tiny images | a product |
| needs on the build PC | `mmdebstrap`, `uidmap` (rootless) or `sudo`; `qemu-user-static` on x86 | `fakeroot` | nothing |
| login | `root` and `dev`, password `stm32mp2` | `root`, password `stm32mp2` | whatever you set |

> **The default password is a bench default**, written in `config/stm32mp257f-dk.conf`
> (`TARGET_PASSWORD`). Change it in `config/local.conf` before the board is on a network you do not control.
> Only a salted SHA-512 hash goes into the image, never the clear text.

## Debian, step by step

`scripts/rootfs.sh` runs `mmdebstrap` (a fast, reproducible `debootstrap`):

```text
mmdebstrap --mode=unshare --architectures=arm64 --variant=minbase \
           --keyring=<Debian's archive key, checksum-pinned> \
           --include=systemd-sysv,udev,dbus,kmod,iproute2,openssh-server,sudo,…,systemd-resolved \
           --customize-hook=scripts/rootfs/debian-customize.sh \
           trixie build/deploy/rootfs-debian-trixie.tar  <main, updates and security mirrors>
```

* `--mode=unshare` makes the files appear root-owned **without** being root, by using a user namespace.
  When that is not allowed (Ubuntu 24.04 restricts it, see [02](02-host-setup.md#rootless-debian-and-the-ubuntu-2404-user-namespace-rule))
  the script runs mmdebstrap under `sudo` instead.
* `--variant=minbase` installs only what Debian marks essential plus `apt`; the package list
  `DEBIAN_PACKAGES` in the config adds a usable system (ssh server, I²C and USB tools, `ethtool`, `htop`).
* The **keyring** is Debian's `debian-archive-keyring` package, downloaded with a pinned sha256, so the
  signatures of every downloaded package are verified even on Ubuntu, which does not ship Debian's newest
  keys.
* `debian-customize.sh` is the only place that turns a bootstrap into a *board image*; read it, it is
  commented line by line. It:

| Action | Why |
| --- | --- |
| writes `/etc/hostname` and `/etc/hosts` | the prompt, DHCP, `sudo` |
| writes `/etc/fstab` with `LABEL=rootfs / ext4 defaults,noatime 0 1` | mount options belong **here**, not on the kernel command line (see [09](09-troubleshooting.md#kernel-panic-with-an-ext4-unknown-parameter-message)) |
| creates user `dev` (groups `sudo`, `dialout`, `video`, …) and sets both passwords | you can log in |
| enables `systemd-networkd` with DHCP on every wired interface (`Name=e*`) | the DK's Ethernet shows up as `end0` |
| deletes the SSH host keys and generates new ones on first start | otherwise every board made from this image has the same keys |
| empties `/etc/machine-id` | systemd makes a unique id on first boot |
| removes the apt package lists | smaller; `apt update` on the board refreshes them |

There is no console-getty line anywhere: `systemd`'s *getty generator* sees `console=ttySTM0,115200` on the
kernel command line and starts `serial-getty@ttySTM0` by itself.

## Alpine, step by step

The Alpine *minirootfs* is a tarball of a few MB published with a `.sha256` file; the script fetches both and
verifies the sum. It has no init system configured, so the script writes a small `/etc/inittab` for
BusyBox `init`: mount `/proc`, `/sys`, `/dev/pts`; start `syslogd`; run `mdev` and a small `coldplug` script that
loads a kernel module for every device found (BusyBox has no `udev`); and start `/sbin/console-getty`, a
three-line script that reads `console=` from `/proc/cmdline` and starts `getty` on it (115200 baud). All
of it runs inside a single `fakeroot` session so the files end up root-owned without root.

## The `Image` is not in here

The kernel, its device trees and its modules are **not** in the rootfs tarball: `image.sh` unpacks the
kernel overlay (`build/deploy/kernel.tar.gz`) on top of it. That is what makes it possible to replace a
kernel on a finished card without touching the rest ([07](07-flashing-and-booting.md)) and to use a rootfs
you did not build.

## Bring your own

Any tarball works if it contains a complete `/`. Two things to check:

1. **An `/sbin/init`** (or `/init`, or whatever `init=` you add to the command line in
   `scripts/image.sh`).
2. **A login on `ttySTM0`.** If it is a systemd system, nothing to do; for another init, start a getty
   on the kernel console.

Then `./build.sh -r /path/to/rootfs.tar.zst image`. The image builder detects gz/xz/zst/bz2 on its own.

Next: [06 · The SD card image](06-sdcard-image.md).
