#!/usr/bin/env bash
# =============================================================================
#  scripts/image.sh - assemble a complete, flashable SD card image
# =============================================================================
#
#  Inputs (produced by the other steps):
#    build/deploy/tf-a-stm32mp157f-dk2.stm32   BL2          (scripts/firmware.sh tfa)
#    build/deploy/fip.bin                     the FIP      (scripts/firmware.sh fip)
#    build/deploy/kernel.tar.gz               kernel+dtb+modules (scripts/kernel.sh)
#    build/deploy/rootfs.tar                  root filesystem    (scripts/rootfs.sh)
#
#  Output:
#    build/deploy/stm32mp157f-dk2-<rootfs>-<date>.img  (+ .bmap)
#    build/deploy/sdcard.img -> the newest one
#
#  Layout written (a GPT disk; see docs/06-sdcard-image.md and docs/images/sd-layout.svg):
#
#    sector 0-33     protective MBR + GPT header + partition entries
#    1 MiB           p1 fsbl1       BL2     <- the Boot ROM looks for this NAME
#    1.25 MiB        p2 fsbl2       BL2     <- ... and falls back to this one
#    1.5 MiB         p3 fip          the FIP <- BL2 looks for this TYPE GUID
#    9 MiB           p4 u-boot-env   U-Boot saves its environment here (found by NAME)
#    16 MiB          p5 rootfs       ext4, bootable flag set
#                      /boot/extlinux/extlinux.conf   <- U-Boot's distro boot reads this
#                      /boot/zImage, /boot/stm32mp157f-dk2.dtb
#                      /lib/modules/<ver>/ ... the rest of the root filesystem
#
#  NO root/sudo needed: the ext4 filesystem is created from a directory with
#  `mke2fs -d` inside a `fakeroot` session, and partitioning happens on a
#  regular file.
# =============================================================================
# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
strict_mode
load_config

BL2_BIN="$DEPLOY_DIR/tf-a-${TFA_DTB%.dtb}.stm32"
FIP_BIN="$DEPLOY_DIR/fip.bin"
KERNEL_TAR="$DEPLOY_DIR/kernel.tar.gz"
ROOTFS_TAR="$DEPLOY_DIR/rootfs.tar"
STAGE="$WORK_DIR/image-rootfs"
EXT4_IMG="$WORK_DIR/rootfs.ext4"
DTB_NAME="$(basename "${KERNEL_DTBS%% *}")"   # first device tree: the one extlinux.conf names

SECTOR=512
mb_to_s() { echo $(( $1 * 1024 * 1024 / SECTOR )); }
kb_to_s() { echo $(( $1 * 1024 / SECTOR )); }

main() {
  start_log "image"
  need_cmd fakeroot mke2fs sfdisk dd truncate tar
  section "Assembling SD card image"
  need_file "$BL2_BIN" "$FIP_BIN" "$KERNEL_TAR" "$ROOTFS_TAR"

  # Sector numbers of every partition. Each one starts where the previous ends,
  # except the environment (fixed by U-Boot's CONFIG_ENV_OFFSET) and the rootfs.
  local fsbl1_s=2048                                   # 1 MiB: first aligned sector after the GPT
  local fsbl2_s=$(( fsbl1_s + $(kb_to_s "$FSBL_SIZE_KB") ))
  local fip_s=$(( fsbl2_s + $(kb_to_s "$FSBL_SIZE_KB") ))
  local env_s; env_s=$(mb_to_s "$ENV_START_MB")
  local root_s; root_s=$(mb_to_s "$ROOTFS_PART_START_MB")
  local fsbl_len; fsbl_len=$(kb_to_s "$FSBL_SIZE_KB")
  local fip_len; fip_len=$(kb_to_s "$FIP_SIZE_KB")
  local env_len; env_len=$(kb_to_s "$ENV_SIZE_KB")

  if [[ $DRY_RUN != 1 ]]; then
    (( $(stat -c %s "$BL2_BIN") <= FSBL_SIZE_KB * 1024 )) || die "BL2 is larger than the ${FSBL_SIZE_KB} KiB fsbl partition; raise FSBL_SIZE_KB"
    (( $(stat -c %s "$FIP_BIN") <= FIP_SIZE_KB * 1024 )) || die "fip.bin is larger than the ${FIP_SIZE_KB} KiB fip partition; raise FIP_SIZE_KB"
    (( fip_s + fip_len <= env_s )) || die "the fip partition would run into the U-Boot environment at ${ENV_START_MB} MiB"
    (( env_s + env_len <= root_s )) || die "the environment partition would run into the rootfs at ${ROOTFS_PART_START_MB} MiB"
  fi

  local rootfs_name
  rootfs_name=$(basename "$(readlink -f "$ROOTFS_TAR")"); rootfs_name=${rootfs_name%%.tar*}; rootfs_name=${rootfs_name#rootfs-}
  local img
  img="$DEPLOY_DIR/stm32mp157f-dk2-${rootfs_name}-$(date +%Y%m%d-%H%M).img"

  # What U-Boot's distro boot reads. KERNEL/FDT paths start at the root of the
  # partition that holds extlinux.conf. root= names the partition by PARTUUID
  # (set in the GPT below), so it does not matter whether Linux calls the SD
  # card mmcblk0 or mmcblk1.
  local append="root=PARTUUID=$ROOTFS_PARTUUID console=$TARGET_CONSOLE,$CONSOLE_BAUD $KERNEL_CMDLINE_EXTRA"

  # ---------------------------------------------------------------------------
  # 1) Stage the full root filesystem and turn it into an ext4 image.
  #    One fakeroot session = files are owned by root:root in the image.
  # ---------------------------------------------------------------------------
  run "Start from an empty staging directory" rm -rf "$STAGE" "$EXT4_IMG"
  run "Create it" mkdir -p "$STAGE"

  explain "Inside fakeroot:" \
          "  - unpack the rootfs tarball (tar detects gz/xz/zst/bz2 by itself)" \
          "  - unpack the kernel overlay on top. --keep-directory-symlink matters:" \
          "    on Debian /lib is a symlink to /usr/lib and must stay one" \
          "  - write /boot/extlinux/extlinux.conf, the file U-Boot's distro boot looks for" \
          "  - size the filesystem (content + ${IMAGE_EXTRA_MB} MiB + 10% ext4 overhead)" \
          "  - mke2fs -d copies the staged tree into a new ext4 image"
  run "Build the ext4 root filesystem image (as fake root)" \
    fakeroot -- bash -euc '
      stage=$1 rootfs=$2 kernel=$3 img=$4 extra=$5 label=$6 dtb=$7 append=$8
      tar -xpf "$rootfs" -C "$stage" --numeric-owner
      tar -xpf "$kernel" -C "$stage" --numeric-owner --keep-directory-symlink
      mkdir -p "$stage/boot/extlinux"
      cat > "$stage/boot/extlinux/extlinux.conf" <<EOF
# U-Boot distro boot ("sysboot") reads this file: /boot/extlinux/extlinux.conf.
# Paths are relative to the root of this partition.
DEFAULT linux
TIMEOUT 10
MENU TITLE Boot menu

LABEL linux
  MENU LABEL Linux
  LINUX /boot/zImage
  FDT /boot/$dtb
  APPEND $append

LABEL linux-debug
  MENU LABEL Linux, verbose (loglevel 7, deferred probes listed after 5 s)
  LINUX /boot/zImage
  FDT /boot/$dtb
  APPEND $append loglevel=7 deferred_probe_timeout=5
EOF
      chmod 0644 "$stage/boot/extlinux/extlinux.conf"
      used=$(du -s --block-size=1M "$stage" | cut -f1)
      size=$(( used + extra + used / 10 + 64 ))
      echo "  rootfs content: ${used} MiB -> ext4 size: ${size} MiB"
      mke2fs -q -F -t ext4 -L "$label" -d "$stage" "$img" "${size}M"
    ' _ "$STAGE" "$ROOTFS_TAR" "$KERNEL_TAR" "$EXT4_IMG" "$IMAGE_EXTRA_MB" "$ROOTFS_LABEL" "$DTB_NAME" "$append"

  # ---------------------------------------------------------------------------
  # 2) Create the disk image file: partition table + firmware + filesystem
  # ---------------------------------------------------------------------------
  local fs_bytes=0
  [[ $DRY_RUN == 1 ]] || fs_bytes=$(stat -c %s "$EXT4_IMG")
  # +1 MiB at the end: GPT keeps a backup copy of its table at the very end of the disk.
  local total_mb=$(( ROOTFS_PART_START_MB + (fs_bytes + 1024*1024 - 1) / (1024*1024) + 1 ))

  run "Remove a previous image with the same name" rm -f "$img"
  run "Create an empty (sparse) ${total_mb} MiB image file" truncate -s "${total_mb}M" "$img"
  # sfdisk reads a small script. Fields: start/size in sectors, type = GPT type
  # GUID, name = what the Boot ROM and BL2 search for, uuid = the PARTUUID that
  # root= refers to, attrs=LegacyBIOSBootable = the flag U-Boot's distro boot
  # looks for ("part list -bootable") to decide which partition to scan.
  local script
  script="label: gpt
label-id: 6d703135-0000-4000-8000-000000000000
unit: sectors
first-lba: 2048

start=$fsbl1_s, size=$fsbl_len, type=$GUID_ST_FSBL, name=fsbl1
start=$fsbl2_s, size=$fsbl_len, type=$GUID_ST_FSBL, name=fsbl2
start=$fip_s, size=$fip_len, type=$GUID_ST_FIP, name=fip
start=$env_s, size=$env_len, type=$GUID_ST_FSBL, name=u-boot-env
start=$root_s, type=$GUID_LINUX_FS, name=rootfs, uuid=$ROOTFS_PARTUUID, attrs=LegacyBIOSBootable"
  explain "GPT partition table written with sfdisk:" "$(printf '%s\n' "$script" | sed 's/^/    /')"
  run_sh "Write the GPT partition table" \
    "printf '%s\\n' '$script' | sfdisk --quiet '$img'"
  # conv=notrunc : write into the existing file instead of truncating it
  run "Write BL2 into partition fsbl1 (sector $fsbl1_s)" \
    dd if="$BL2_BIN" of="$img" bs=$SECTOR seek="$fsbl1_s" conv=notrunc status=none
  run "Write the same BL2 into fsbl2 (sector $fsbl2_s), the ROM's fallback copy" \
    dd if="$BL2_BIN" of="$img" bs=$SECTOR seek="$fsbl2_s" conv=notrunc status=none
  run "Write the FIP into partition fip (sector $fip_s)" \
    dd if="$FIP_BIN" of="$img" bs=$SECTOR seek="$fip_s" conv=notrunc status=none
  # conv=sparse : skip writing blocks of zeros, keeps the file small on disk
  run "Copy the ext4 filesystem into partition rootfs (sector $root_s)" \
    dd if="$EXT4_IMG" of="$img" bs=$SECTOR seek="$root_s" conv=notrunc,sparse status=none

  # ---------------------------------------------------------------------------
  # 3) Helpers for fast flashing and housekeeping
  # ---------------------------------------------------------------------------
  if command -v bmaptool >/dev/null; then
    # A block map lists only the blocks that contain data, so
    # `bmaptool copy` writes ~the used size instead of the full image.
    run "Create a block map (.bmap) for fast flashing with bmaptool" \
      bmaptool -q create -o "$img.bmap" "$img"
  fi
  run "Point sdcard.img at the newest image" ln -sfn "$(basename "$img")" "$DEPLOY_DIR/sdcard.img"
  [[ -f $img.bmap ]] && run "...and sdcard.img.bmap at its block map" ln -sfn "$(basename "$img").bmap" "$DEPLOY_DIR/sdcard.img.bmap"
  run "Free the staging area" rm -rf "$STAGE" "$EXT4_IMG"

  if [[ $DRY_RUN != 1 ]]; then
    section "Done"
    sfdisk --verify "$img" | sed 's/^/  /'
    sfdisk -l "$img" | sed 's/^/  /'
    info "SD card image: $img ($(hsize "$img") on disk, $(du -h --apparent-size "$img" | cut -f1) apparent)"
    info "Flash it with:  ./build.sh flash -d /dev/sdX"
  fi
}

main "$@"
