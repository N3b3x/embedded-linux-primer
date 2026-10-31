#!/usr/bin/env bash
# =============================================================================
#  scripts/image.sh - assemble a complete, flashable SD card image
# =============================================================================
#
#  Inputs (produced by the other steps):
#    build/deploy/BOOT.BIN        first-stage loader: U-Boot SPL      (scripts/uboot.sh)
#    build/deploy/u-boot.img      U-Boot proper, loaded by the SPL    (scripts/uboot.sh)
#    build/deploy/kernel.tar.gz   zImage + dtb (fat/), modules (rootfs/)  (scripts/kernel.sh)
#    build/deploy/rootfs.tar      root filesystem                     (scripts/rootfs.sh)
#
#  Output:
#    build/deploy/eclypse-z7-<rootfs>-<date>.img  (+ .bmap)
#    build/deploy/sdcard.img -> the newest one
#
#  Layout written (an MBR disk, because the Zynq BootROM does not read GPT;
#  see docs/06-sdcard-image.md and docs/images/sd-layout.svg):
#
#    sector 0        MBR: boot code area + disk signature + 4 partition entries
#    1 MiB           p1  FAT32, label BOOT, bootable flag
#                          /BOOT.BIN                  <- the BootROM opens this
#                          /u-boot.img                <- the SPL loads this
#                          /extlinux/extlinux.conf    <- U-Boot's distro boot reads this
#                          /zImage  /zynq-eclypse-z7.dtb
#    301 MiB         p2  ext4, label rootfs: the root filesystem + /lib/modules
#
#  NO root/sudo needed: the ext4 filesystem is created from a directory with
#  `mke2fs -d` inside a `fakeroot` session, the FAT with mkfs.vfat + mtools on a
#  regular file, and the partitioning happens on a regular file.
# =============================================================================
# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
strict_mode
load_config

BOOT_BIN="$DEPLOY_DIR/BOOT.BIN"
UBOOT_IMG="$DEPLOY_DIR/u-boot.img"
KERNEL_TAR="$DEPLOY_DIR/kernel.tar.gz"
ROOTFS_TAR="$DEPLOY_DIR/rootfs.tar"
STAGE="$WORK_DIR/image-rootfs"
KOVERLAY="$WORK_DIR/image-kernel"
EXT4_IMG="$WORK_DIR/rootfs.ext4"
FAT_IMG="$WORK_DIR/boot.fat"
DTB_NAME="$(basename "${KERNEL_DTBS%% *}")"   # first device tree: the one extlinux.conf names

SECTOR=512
mb_to_s() { echo $(( $1 * 1024 * 1024 / SECTOR )); }

main() {
  start_log "image"
  need_cmd fakeroot mke2fs mkfs.vfat mcopy mmd sfdisk dd truncate tar
  section "Assembling SD card image"
  need_file "$BOOT_BIN" "$UBOOT_IMG" "$KERNEL_TAR" "$ROOTFS_TAR"

  # Sector numbers of both partitions. p1 starts at 1 MiB (aligned, and clear of the MBR);
  # p2 starts right after it.
  local boot_s boot_len root_s
  boot_s=$(mb_to_s "$BOOT_PART_START_MB")
  boot_len=$(mb_to_s "$BOOT_PART_SIZE_MB")
  root_s=$(( boot_s + boot_len ))

  local rootfs_name
  rootfs_name=$(basename "$(readlink -f "$ROOTFS_TAR")"); rootfs_name=${rootfs_name%%.tar*}; rootfs_name=${rootfs_name#rootfs-}
  local img
  img="$DEPLOY_DIR/eclypse-z7-${rootfs_name}-$(date +%Y%m%d-%H%M).img"

  # What U-Boot's distro boot reads. KERNEL/FDT paths start at the root of the FAT partition.
  # root= names the partition by its MBR PARTUUID: "<disk signature>-<partition number>".
  local partuuid="${DISK_SIGNATURE}-02"
  local append="root=PARTUUID=$partuuid console=$TARGET_CONSOLE,$CONSOLE_BAUD $KERNEL_CMDLINE_EXTRA"

  # ---------------------------------------------------------------------------
  # 1) Stage the full root filesystem and turn it into an ext4 image.
  #    One fakeroot session = files are owned by root:root in the image.
  # ---------------------------------------------------------------------------
  run "Start from empty staging directories" rm -rf "$STAGE" "$KOVERLAY" "$EXT4_IMG" "$FAT_IMG"
  run "Create them" mkdir -p "$STAGE" "$KOVERLAY"
  run "Unpack the kernel overlay (fat/ for the boot partition, rootfs/ for the modules)" \
    tar -xzf "$KERNEL_TAR" -C "$KOVERLAY"

  explain "Inside fakeroot:" \
          "  - unpack the rootfs tarball (tar detects gz/xz/zst/bz2 by itself)" \
          "  - copy the kernel's rootfs/ half on top (/lib/modules, /boot/config-*)." \
          "    --keep-directory-symlink matters: on Debian /lib is a symlink to /usr/lib" \
          "  - size the filesystem (content + ${IMAGE_EXTRA_MB} MiB + 10% ext4 overhead)" \
          "  - mke2fs -d copies the staged tree into a new ext4 image"
  run "Build the ext4 root filesystem image (as fake root)" \
    fakeroot -- bash -euc '
      stage=$1 rootfs=$2 overlay=$3 img=$4 extra=$5 label=$6
      tar -xpf "$rootfs" -C "$stage" --numeric-owner
      tar -C "$overlay/rootfs" -cf - . | tar -xpf - -C "$stage" --numeric-owner --keep-directory-symlink
      used=$(du -s --block-size=1M "$stage" | cut -f1)
      size=$(( used + extra + used / 10 + 64 ))
      echo "  rootfs content: ${used} MiB -> ext4 size: ${size} MiB"
      mke2fs -q -F -t ext4 -L "$label" -d "$stage" "$img" "${size}M"
    ' _ "$STAGE" "$ROOTFS_TAR" "$KOVERLAY" "$EXT4_IMG" "$IMAGE_EXTRA_MB" "$ROOTFS_LABEL"

  # ---------------------------------------------------------------------------
  # 2) The FAT boot partition: BOOT.BIN, u-boot.img, kernel, device tree, extlinux.conf
  # ---------------------------------------------------------------------------
  local extlinux="$WORK_DIR/extlinux.conf"
  explain "extlinux.conf, the file U-Boot's distro boot (sysboot) looks for. Paths are relative to the" \
          "root of the FAT partition; APPEND is the kernel command line (docs/04-kernel.md)."
  if [[ $DRY_RUN != 1 ]]; then
    cat > "$extlinux" <<CONF
# U-Boot distro boot ("sysboot") reads this file: /extlinux/extlinux.conf on the FAT partition.
DEFAULT linux
TIMEOUT 10
MENU TITLE Boot menu

LABEL linux
  MENU LABEL Linux
  LINUX /$KERNEL_IMAGE
  FDT /$DTB_NAME
  APPEND $append
CONF
  fi
  run "Create an empty FAT image of ${BOOT_PART_SIZE_MB} MiB" truncate -s "${BOOT_PART_SIZE_MB}M" "$FAT_IMG"
  explain "FAT32, 512-byte sectors, 4 KiB clusters, label $BOOT_LABEL. The BootROM reads FAT16 and FAT32."
  run "Format it as FAT32 with 4 KiB clusters (-s 8: 8 sectors per cluster)" mkfs.vfat -F 32 -S 512 -s 8 -n "$BOOT_LABEL" "$FAT_IMG"
  # Order matters a little: BOOT.BIN first, so it sits at the start of the data area.
  run "Copy BOOT.BIN, u-boot.img, the kernel and its device tree into the FAT image" \
    mcopy -i "$FAT_IMG" "$BOOT_BIN" "$UBOOT_IMG" "$KOVERLAY/fat/$KERNEL_IMAGE" "$KOVERLAY/fat/$DTB_NAME" ::
  run "Create the extlinux directory" mmd -i "$FAT_IMG" ::extlinux
  run "Copy extlinux.conf into it" mcopy -i "$FAT_IMG" "$extlinux" ::extlinux/extlinux.conf

  # ---------------------------------------------------------------------------
  # 3) Create the disk image file: partition table + the two filesystems
  # ---------------------------------------------------------------------------
  local fs_bytes=0
  [[ $DRY_RUN == 1 ]] || fs_bytes=$(stat -c %s "$EXT4_IMG")
  local total_mb=$(( BOOT_PART_START_MB + BOOT_PART_SIZE_MB + (fs_bytes + 1024*1024 - 1) / (1024*1024) + 1 ))

  run "Remove a previous image with the same name" rm -f "$img"
  run "Create an empty (sparse) ${total_mb} MiB image file" truncate -s "${total_mb}M" "$img"
  # sfdisk reads a small script. label-id = the 32-bit disk signature (PARTUUID=<it>-0N);
  # type=c is "W95 FAT32 (LBA)", type=83 "Linux"; "bootable" sets the MBR active flag.
  local script
  script="label: dos
label-id: 0x$DISK_SIGNATURE
unit: sectors

start=$boot_s, size=$boot_len, type=c, bootable
start=$root_s, type=83"
  explain "MBR partition table written with sfdisk:" "$(printf '%s\n' "$script" | sed 's/^/    /')"
  run_sh "Write the MBR partition table" \
    "printf '%s\\n' '$script' | sfdisk --quiet '$img'"
  # conv=notrunc : write into the existing file instead of truncating it
  run "Write the FAT filesystem into partition 1 (sector $boot_s)" \
    dd if="$FAT_IMG" of="$img" bs=$SECTOR seek="$boot_s" conv=notrunc,sparse status=none
  # conv=sparse : skip writing blocks of zeros, keeps the file small on disk
  run "Write the ext4 filesystem into partition 2 (sector $root_s)" \
    dd if="$EXT4_IMG" of="$img" bs=$SECTOR seek="$root_s" conv=notrunc,sparse status=none

  # ---------------------------------------------------------------------------
  # 4) Helpers for fast flashing and housekeeping
  # ---------------------------------------------------------------------------
  if command -v bmaptool >/dev/null; then
    run "Create a block map (.bmap) for fast flashing with bmaptool" \
      bmaptool -q create -o "$img.bmap" "$img"
  fi
  run "Point sdcard.img at the newest image" ln -sfn "$(basename "$img")" "$DEPLOY_DIR/sdcard.img"
  [[ -f $img.bmap ]] && run "...and sdcard.img.bmap at its block map" ln -sfn "$(basename "$img").bmap" "$DEPLOY_DIR/sdcard.img.bmap"
  run "Free the staging area" rm -rf "$STAGE" "$KOVERLAY" "$EXT4_IMG" "$FAT_IMG"

  if [[ $DRY_RUN != 1 ]]; then
    section "Done"
    sfdisk --verify "$img" | sed 's/^/  /'
    sfdisk -l "$img" | sed 's/^/  /'
    info "SD card image: $img ($(hsize "$img") on disk, $(du -h --apparent-size "$img" | cut -f1) apparent)"
    info "Flash it with:  ./build.sh flash -d /dev/sdX"
  fi
}

main "$@"
