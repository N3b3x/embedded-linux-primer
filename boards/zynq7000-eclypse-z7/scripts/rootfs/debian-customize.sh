#!/bin/sh
# =============================================================================
#  scripts/rootfs/debian-customize.sh - turn a fresh Debian bootstrap into a
#  bootable system for the board
# =============================================================================
#
#  Called by mmdebstrap (scripts/rootfs.sh) as a --customize-hook, i.e. AFTER
#  all packages are installed and BEFORE the tarball is written:
#
#     debian-customize.sh <rootdir> <hostname> <user> <fs-label> <shadow-file> <boot-label>
#
#  It runs on the build PC with root rights (sudo or a user namespace).
#  Paths are always prefixed with "$ROOT" so we only ever touch the new
#  filesystem. `chroot "$ROOT" <cmd>` runs a 32-bit ARM program inside it; on an
#  x86 or ARM64 PC qemu-user-static executes it transparently.
#
#  Edit this file to customise the Debian image (extra config files, services
#  to enable, ...). Packages are better added via DEBIAN_PACKAGES.
# =============================================================================
set -eu

ROOT=$1        # the new root filesystem
HOSTNAME=$2    # e.g. eclypse-z7
NEWUSER=$3     # e.g. dev
LABEL=$4       # ext4 label of the root partition, e.g. root
SHADOW=$5      # file with "user:<sha512-hash>" lines (never a clear-text password)
BOOTLABEL=$6   # label of the FAT boot partition, e.g. BOOT

echo "debian-customize: configuring $ROOT"

# --- Identity ----------------------------------------------------------------
# The name shown in the shell prompt and announced via DHCP.
echo "$HOSTNAME" > "$ROOT/etc/hostname"
# Make the hostname resolvable locally (sudo complains otherwise).
printf '127.0.0.1\tlocalhost\n127.0.1.1\t%s\n::1\t\tlocalhost ip6-localhost ip6-loopback\n' \
  "$HOSTNAME" > "$ROOT/etc/hosts"

# --- Filesystems -------------------------------------------------------------
# Mount the root partition by its label, so the number Linux gives the SD card does not
# matter. noatime avoids a write on every file read. The FAT boot partition (zImage, DTB,
# extlinux.conf, BOOT.BIN) is mounted at /boot/firmware, like on other SD-card boards, so you
# can replace the kernel from the running board; nofail keeps a missing card from stopping boot.
mkdir -p "$ROOT/boot/firmware"
printf 'LABEL=%s / ext4 defaults,noatime 0 1\nLABEL=%s /boot/firmware vfat defaults,noatime,nofail 0 2\n' \
  "$LABEL" "$BOOTLABEL" > "$ROOT/etc/fstab"

# --- Users -------------------------------------------------------------------
# A normal user that can use sudo, serial ports, audio, video, USB devices.
chroot "$ROOT" useradd --create-home --shell /bin/bash \
  --groups sudo,adm,dialout,audio,video,plugdev "$NEWUSER"
# Set root's and the user's password hashes (chpasswd -e = already encrypted).
chroot "$ROOT" chpasswd -e < "$SHADOW"

# --- Network -----------------------------------------------------------------
# systemd-networkd: DHCP on every wired interface. Their names on this board
# are eth0 or end0 depending on the kernel's naming (systemd predictable names).
mkdir -p "$ROOT/etc/systemd/network"
cat > "$ROOT/etc/systemd/network/20-wired.network" <<'EOF'
[Match]
Name=e*

[Network]
DHCP=yes
EOF
# Start networkd and the DNS resolver at boot.
chroot "$ROOT" systemctl enable systemd-networkd systemd-resolved

# --- SSH ---------------------------------------------------------------------
# Host keys generated now would be identical on every board made from this
# image. Delete them and generate fresh ones when sshd starts. The unit's own
# first ExecStartPre is "sshd -t", which refuses to run without host keys, so ours
# must come first: the empty "ExecStartPre=" line clears the unit's list and we
# put the key generation and the test back in the right order.
rm -f "$ROOT"/etc/ssh/ssh_host_*
mkdir -p "$ROOT/etc/systemd/system/ssh.service.d"
cat > "$ROOT/etc/systemd/system/ssh.service.d/keygen.conf" <<'EOF'
[Service]
ExecStartPre=
ExecStartPre=/usr/bin/ssh-keygen -A
ExecStartPre=/usr/sbin/sshd -t
EOF

# --- First boot --------------------------------------------------------------
# An empty machine-id makes systemd generate a unique one on first boot
# (used for DHCP client IDs, journal, ...).
: > "$ROOT/etc/machine-id"

# --- Size --------------------------------------------------------------------
# Package lists and caches are re-downloaded by `apt update` on the board.
rm -rf "$ROOT"/var/lib/apt/lists/* "$ROOT"/var/cache/apt/*.bin

echo "debian-customize: done"
