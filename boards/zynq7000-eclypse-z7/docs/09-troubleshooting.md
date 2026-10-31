# 09 · Troubleshooting

Organised by **the last thing you saw**. The first half is about the build, the second about the board. Every
build step writes a log to `build/logs/<step>.log` (a link to the newest one), and the error trap prints the
failing command, the script line and the log path.

> The board has not been booted on hardware by the authors of this repository (see the status table in the
> [README](../README.md)). The build-time entries are things that really happened while this board was brought
> up. The boot-time entries say what the sources print and what to check; the shorter, log-line-first version for
> the day you power the board on is [14 · First-boot checklist](14-first-boot-checklist.md).

## Build time

### `E: install arch-test for foreign architecture support` (mmdebstrap)

`mmdebstrap` needs the `arch-test` package to check that it can run `armhf` programs. `./build.sh deps --install`
installs it; by hand `sudo apt install arch-test`.

### `armhf binfmt handler missing: sudo apt install qemu-user-static binfmt-support`

The Debian root filesystem is 32-bit ARM and is bootstrapped by running its programs under qemu, on an x86 **and**
on an ARM64 PC (most 64-bit Arm CPUs cannot run 32-bit code). Install `qemu-user-static binfmt-support`. In a
container, run it `--privileged` and `mount -t binfmt_misc none /proc/sys/fs/binfmt_misc`
([02](02-host-setup.md#using-a-container-on-macos-or-windows)). The check accepts any `binfmt_misc` entry for
32-bit ARM ELF files, whatever it is called. `./build.sh -r alpine rootfs` needs none of this.

### `ssh.service` fails on the Debian image (`sshd: no hostkeys available -- exiting`)

Seen on a first image: the unit's own `ExecStartPre=/usr/sbin/sshd -t` ran before our key generation. The
customize hook now clears the unit's list and runs `ssh-keygen -A` first. If you edit that hook, keep the order.

### `error: unrecognized option '--rcfile'` / other `shellcheck` surprises

`shellcheck` finds `.shellcheckrc` in a parent directory of the script, not through an option. Run it from a copy of
the board directory inside a tree that has the repository's `.shellcheckrc` above it.

### `fatal error: asm/arch/ps7_init_gpl.h: No such file` or `-Werror=strict-prototypes` (U-Boot)

The PS7 file was not prepared. `scripts/lib/ps7_prepare.py` turns `int ps7_init()` into `int ps7_init(void)`;
if you pass your own file with `PS7_INIT_SRC`, it goes through the same script. A file from another tool may
need more edits: compare it with the one in `build/work/ps7-init/`.

### `PS7_INIT_SRC=… does not exist`, or `expected exactly one ps7_init_gpl.c`

`PS7_INIT_SRC` must be a `ps7_init_gpl.c` (with the `.h` beside it), a directory with both, or a zip (`.hdf`/`.xsa`)
that contains both exactly once.

### `sha256sum: WARNING: 1 computed checksum did NOT match` on `system.hdf`

The download is not the pinned file (a proxy page, a truncated transfer, or the project moved the file: it is
pinned by **commit**, so a moved file is a 404, not a different file). Delete `build/downloads/system.hdf` and try
again, or supply your own with `PS7_INIT_SRC`.

### `spl/boot.bin is … bytes: larger than the 192 KiB the BootROM can load`

The SPL grew (a feature added in `config/uboot/`). The BootROM copies the payload into the on-chip RAM and the
top 64 KiB of the 256 KiB are not available. Switch the feature off for the SPL, or use the vendor route
([03](03-uboot-spl.md#appendix-the-vendor-route-fsbl-and-bootgen)).

### `CONFIG_… is not built in: …` (kernel)

A fragment switched off an option the boot path needs. The list is `REQUIRED_BUILTIN` in `scripts/kernel.sh`.

### The kernel build fails with odd "No such file" errors on macOS

The kernel tree has files that differ only in letter case. Build on a Linux file system: a Docker volume or a
Linux VM disk.

### `ERROR: unknown option: -j6`

Options that take a value are separate words: `./build.sh -j 6 kernel`.

### Debian rootfs fails to start the namespace on Ubuntu 24.04

`sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`, or let the script fall back to `sudo`, or use
`./build.sh -r alpine rootfs`.

### `sed -i` or `stat -c` fails in the scripts

The scripts are for GNU userland (Linux). Run them in a Linux container on macOS.

## Board time: nothing on the console

1. **Right port, right speed?** 115200 8N1, the **second** FTDI channel (`ttyUSB1`, `…-if01-port0`). The ports vanish
   and reappear at every power cycle ([07](07-flashing-and-booting.md#3-connect-the-serial-console)).
2. **JP5 on `SD`** (the two rightmost pins), and a **full power cycle** after moving it.
3. **Is the card written and readable?** Check it on your PC: partition 1 FAT32, `BOOT.BIN` in the root, 131,676
   bytes: `mdir -i /dev/sdX1 ::`. The BootROM stays silent for anything wrong with the file or its header.
4. **Does the board work at all?** Put JP5 on `QSPI`: if a factory image is in the flash it boots and talks; if it does,
   power, UART and cable are fine, and the problem is the card or its files.
5. Read [14](14-first-boot-checklist.md): it tells which line you *should* see first.

## The SPL starts, then stops

| Last line | Likely cause |
| --- | --- |
| nothing after the banner, no `Trying to boot from` | `ps7_init` ran, the console works, but the SPL stops before it chooses a device. Look at `Unsupported boot mode selected` (JP5 in an odd position) |
| `Trying to boot from MMC1` then `Error: -…` (negative number) | the SD host or the FAT partition could not be read, or `u-boot.img` is missing/misnamed. Check the card on your PC |
| `SPL: failed to boot from all boot devices` | same, after every device was tried |
| garbage characters | the UART clock is wrong: `ps7_init` was made for a different board (clock/PLL settings), or the terminal is not at 115200 |
| the board resets in a loop (the banner repeats) | the SPL crashed after `ps7_init`: a `ps7_init` for another memory (DDR training fails) is the first thing to suspect |

## U-Boot starts but Linux does not

You see the U-Boot banner and `Hit any key to stop autoboot`, then either a prompt (`Zynq>`) or a loop.

```text
Zynq> mmc list                         # mmc@e0100000: 0
Zynq> part list mmc 0                  # two partitions, the first marked bootable ("Bootable")
Zynq> ls mmc 0:1 /                     # BOOT.BIN u-boot.img zImage zynq-eclypse-z7.dtb extlinux
Zynq> printenv boot_targets
Zynq> load mmc 0:1 ${kernel_addr_r} zImage && load mmc 0:1 ${fdt_addr_r} zynq-eclypse-z7.dtb
Zynq> setenv bootargs root=PARTUUID=5a796e71-02 console=ttyPS0,115200 rootwait rw earlycon
Zynq> bootz ${kernel_addr_r} - ${fdt_addr_r}
```

* `No ethernet found` / `Could not get PHY for eth0`: harmless for an SD boot; the PHY is not needed to reach Linux.
* `Scanning mmc 0:1…` but no `Found /extlinux/extlinux.conf`: the file is not at `extlinux/extlinux.conf` on
  partition 1 (some tools lower-case or move it), or the partition is not FAT.
* `** Unable to read file /zImage **`: the name differs; `ls` shows what is there.
* `Wrong image format for "source" command`, `QSPI: SCRIPT FAILED`, `JTAG: SCRIPT FAILED`: ordinary, from
  boot targets that are tried before `mmc0` and fail fast.
* `Bad Linux ARM zImage magic!`: `zImage` is the wrong file (an `Image` from a 64-bit build?).

## The kernel starts but does not reach a login

| Last kernel line | Cause |
| --- | --- |
| `Starting kernel ...` and then **nothing** | the kernel started but its console is silent: `earlycon` prints the very first lines; if even those are missing, check that the DTB is the one for this board (`Machine model: Digilent Eclypse Z7`) and that you really used `console=ttyPS0,115200` |
| `Waiting for root device PARTUUID=5a796e71-02...` forever | the SD card is not found: the SDHCI driver did not bind (`mmc0:` lines missing) or the card is not seen by Linux (CD pin); compare with the QEMU log in [07](07-flashing-and-booting.md) |
| `VFS: Cannot open root device "PARTUUID=…"` | no `mmcblk0p2`, or a different disk signature: re-flash |
| `EXT4-fs … bad geometry`, `VFS: Unable to mount root fs` | the ext4 partition is truncated: `./build.sh flash --expand` or a failed write |
| `Kernel panic - not syncing: No working init found` | the root filesystem is not 32-bit ARM, or `/sbin/init` is missing |
| `Kernel panic … Attempted to kill init! exitcode=0x00007f00` and similar | an `arm64` root filesystem on a 32-bit kernel |

## Linux runs, the network does not

* `macb … Could not attach PHY (-19)` / `MDIO device at address 1 is missing`: the PHY did not answer. Check the
  cable's link LED, and that the kernel's `reset-gpios` line (MIO 9) is what your board revision needs.
* No DHCP lease: `networkctl` and `journalctl -u systemd-networkd`.

Next: [10 · Versions](10-versions.md).
