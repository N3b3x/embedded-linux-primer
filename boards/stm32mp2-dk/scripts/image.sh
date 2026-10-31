#!/usr/bin/env bash
# =============================================================================
#  scripts/image.sh - assemble a complete, flashable SD card image
# =============================================================================
#
#  Inputs (produced by the other steps):
#    build/deploy/tf-a-stm32mp257f-dk.stm32   BL2          (scripts/firmware.sh tfa)
#    build/deploy/fip.bin                     the FIP      (scripts/firmware.sh fip)
#    build/deploy/kernel.tar.gz               kernel+dtb+modules (scripts/kernel.sh)
#    build/deploy/rootfs.tar                  root filesystem    (scripts/rootfs.sh)
#
#  Output:
#    build/deploy/stm32mp257f-dk-<rootfs>-<date>.img  (+ .bmap)
#    build/deploy/sdcard.img -> the newest one
#
#  Layout written (a GPT disk; see docs/06-sdcard-image.md and docs/images/sd-layout.svg):
#
#    sector 0-33     protective MBR + GPT header + partition entries
#    1 MiB           p1 fsbla1       BL2     <- the Boot ROM looks for this NAME
#    1.25 MiB        p2 fsbla2       BL2     <- ... and falls back to this one
#    1.5 MiB         p3 fip          the FIP <- BL2 looks for this TYPE GUID
#    9 MiB           p4 u-boot-env   U-Boot saves its environment here (found by NAME)
#    16 MiB          p5 rootfs       ext4, bootable flag set
#                      /boot/extlinux/extlinux.conf   <- U-Boot's distro boot reads this
#                      /boot/Image, /boot/<the device trees>
#                      /lib/modules/<ver>/ ... the rest of the root filesystem
#
#  STACK=st writes ST's own layout instead (IMAGE_PARTITIONS in config/stack-st.conf):
#  fsbla1 at sector 34, then back to back: fsbla2, metadata1, metadata2, fip-a, fip-b,
#  u-boot-env; rootfs at 16 MiB. metadata.bin (the FWU metadata) goes into both metadata
#  partitions and the same FIP into both fip-a and fip-b.
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
META_BIN="$DEPLOY_DIR/metadata.bin"
KERNEL_TAR="$DEPLOY_DIR/kernel.tar.gz"
ROOTFS_TAR="$ROOTFS_DEPLOY_DIR/rootfs.tar"
STAGE="$WORK_DIR/image-rootfs"
EXT4_IMG="$WORK_DIR/rootfs.ext4"

SECTOR=512
mb_to_s() { echo $(( $1 * 1024 * 1024 / SECTOR )); }
kb_to_s() { echo $(( $1 * 1024 / SECTOR )); }

# What U-Boot's distro boot reads: one LABEL per device tree in KERNEL_DTBS. The first is
# the default; the others are boot-menu entries (TIMEOUT 30 = three seconds to press a key on
# the serial console). KERNEL/FDT paths start at the root of the partition that holds the file.
# root= names the partition by PARTUUID (set in the GPT below), so it does not matter whether
# Linux calls the SD card mmcblk0 or mmcblk1.
extlinux_conf() {
  local append=$1 d name n=0 label menu
  printf '%s\n' "# U-Boot distro boot (\"sysboot\") reads this file: /boot/extlinux/extlinux.conf." \
    "# Paths are relative to the root of this partition." \
    "DEFAULT linux" "TIMEOUT 30" "MENU TITLE Boot menu"
  for d in $KERNEL_DTBS; do
    name=$(basename "$d")
    label=linux; menu="Linux with $name (default)"
    if ((n > 0)); then label="linux-${name%.dtb}"; menu="Linux with $name"; fi
    printf '\nLABEL %s\n  MENU LABEL %s\n  LINUX /boot/%s\n  FDT /boot/%s\n  APPEND %s\n' \
      "$label" "$menu" "$KERNEL_IMAGE" "$name" "$append"
    n=$((n + 1))
  done
}

main() {
  start_log "image"
  need_cmd fakeroot mke2fs sfdisk dd truncate tar
  section "Assembling SD card image ($STACK stack)"
  need_file "$BL2_BIN" "$FIP_BIN" "$KERNEL_TAR" "$ROOTFS_TAR"
  [[ -z $METADATA_PARTITIONS ]] || need_file "$META_BIN"

  # Start sector and length of every partition, in the order of IMAGE_PARTITIONS. Each one
  # starts where the previous ends, except the environment on the mainline stack (it sits
  # where U-Boot's fallback offset CONFIG_ENV_OFFSET says) and the rootfs.
  local -A p_start=() p_len=()
  local fsbl_len meta_len fip_len env_len root_s env_s=0 cur n len
  fsbl_len=$(kb_to_s "$FSBL_SIZE_KB"); meta_len=$(kb_to_s "$META_SIZE_KB")
  fip_len=$(kb_to_s "$FIP_SIZE_KB");   env_len=$(kb_to_s "$ENV_SIZE_KB")
  root_s=$(mb_to_s "$ROOTFS_PART_START_MB")
  [[ $ENV_START_MB == auto ]] || env_s=$(mb_to_s "$ENV_START_MB")
  cur=$FSBL1_START_SECTOR
  for n in $IMAGE_PARTITIONS; do
    case $n in
      fsbla*)     len=$fsbl_len ;;
      metadata*)  len=$meta_len ;;
      fip*)       len=$fip_len ;;
      u-boot-env) len=$env_len
                  if ((env_s != 0)); then
                    ((cur <= env_s)) || die "the partitions before u-boot-env would run into the environment at ${ENV_START_MB} MiB"
                    cur=$env_s
                  fi ;;
      rootfs)     len=0
                  ((cur <= root_s)) || die "the partitions before rootfs would run into it at ${ROOTFS_PART_START_MB} MiB"
                  cur=$root_s ;;
      *) die "unknown partition '$n' in IMAGE_PARTITIONS" ;;
    esac
    p_start[$n]=$cur; p_len[$n]=$len; cur=$(( cur + len ))
  done

  if [[ $DRY_RUN != 1 ]]; then
    (( $(stat -c %s "$BL2_BIN") <= FSBL_SIZE_KB * 1024 )) || die "BL2 is larger than the ${FSBL_SIZE_KB} KiB fsbla partition; raise FSBL_SIZE_KB"
    (( $(stat -c %s "$FIP_BIN") <= FIP_SIZE_KB * 1024 )) || die "fip.bin is larger than the ${FIP_SIZE_KB} KiB fip partition; raise FIP_SIZE_KB"
  fi

  local rootfs_name
  rootfs_name=$(basename "$(readlink -f "$ROOTFS_TAR")"); rootfs_name=${rootfs_name%%.tar*}; rootfs_name=${rootfs_name#rootfs-}
  local img
  # (the ST stack's image says so in its name, so two images cannot be mixed up on a desk)
  local tag=""; [[ $STACK != st ]] || tag="st-"
  img="$DEPLOY_DIR/stm32mp257f-dk-${tag}${rootfs_name}-$(date +%Y%m%d-%H%M).img"

  local append="root=PARTUUID=$ROOTFS_PARTUUID $KERNEL_CMDLINE_EXTRA console=$TARGET_CONSOLE,$CONSOLE_BAUD"
  local extlinux; extlinux=$(extlinux_conf "$append")

  # ---------------------------------------------------------------------------
  # 1) Stage the full root filesystem and turn it into an ext4 image.
  #    One fakeroot session = files are owned by root:root in the image.
  # ---------------------------------------------------------------------------
  run "Start from an empty staging directory" rm -rf "$STAGE" "$EXT4_IMG"
  run "Create it" mkdir -p "$STAGE"

  local ext_lines=()
  mapfile -t ext_lines <<<"$extlinux"
  explain "Inside fakeroot:" \
          "  - unpack the rootfs tarball (tar detects gz/xz/zst/bz2 by itself)" \
          "  - unpack the kernel overlay on top. --keep-directory-symlink matters:" \
          "    on Debian /lib is a symlink to /usr/lib and must stay one" \
          "  - write /boot/extlinux/extlinux.conf, the file U-Boot's distro boot looks for:"
  explain "${ext_lines[@]/#/      | }"
  explain "  - size the filesystem (content + ${IMAGE_EXTRA_MB} MiB + 10% ext4 overhead)" \
          "  - mke2fs -d copies the staged tree into a new ext4 image"
  run "Build the ext4 root filesystem image (as fake root)" \
    fakeroot -- bash -euc '
      stage=$1 rootfs=$2 kernel=$3 img=$4 extra=$5 label=$6 extlinux=$7
      tar -xpf "$rootfs" -C "$stage" --numeric-owner
      tar -xpf "$kernel" -C "$stage" --numeric-owner --keep-directory-symlink
      mkdir -p "$stage/boot/extlinux"
      printf "%s\n" "$extlinux" > "$stage/boot/extlinux/extlinux.conf"
      chmod 0644 "$stage/boot/extlinux/extlinux.conf"
      used=$(du -s --block-size=1M "$stage" | cut -f1)
      size=$(( used + extra + used / 10 + 64 ))
      echo "  rootfs content: ${used} MiB -> ext4 size: ${size} MiB"
      mke2fs -q -F -t ext4 -L "$label" -d "$stage" "$img" "${size}M"
    ' _ "$STAGE" "$ROOTFS_TAR" "$KERNEL_TAR" "$EXT4_IMG" "$IMAGE_EXTRA_MB" "$ROOTFS_LABEL" "$extlinux"

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
  # first-lba matters: sfdisk would otherwise start at 2048 and refuse the ST layout's sector 34.
  local script="label: gpt
label-id: 6d703200-0000-4000-8000-000000000000
unit: sectors
first-lba: $FSBL1_START_SECTOR
"
  for n in $IMAGE_PARTITIONS; do
    case $n in
      fsbla*|metadata*|u-boot-env) script+=$'\n'"start=${p_start[$n]}, size=${p_len[$n]}, type=$GUID_ST_FSBL, name=$n" ;;
      fip-a) script+=$'\n'"start=${p_start[$n]}, size=${p_len[$n]}, type=$GUID_ST_FIP, name=$n, uuid=$FIP_A_PARTUUID" ;;
      fip-b) script+=$'\n'"start=${p_start[$n]}, size=${p_len[$n]}, type=$GUID_ST_FIP, name=$n, uuid=$FIP_B_PARTUUID" ;;
      fip)   script+=$'\n'"start=${p_start[$n]}, size=${p_len[$n]}, type=$GUID_ST_FIP, name=$n" ;;
      rootfs) script+=$'\n'"start=${p_start[$n]}, type=$GUID_LINUX_FS, name=$n, uuid=$ROOTFS_PARTUUID, attrs=LegacyBIOSBootable" ;;
    esac
  done
  explain "GPT partition table written with sfdisk:" "$(printf '%s\n' "$script" | sed 's/^/    /')"
  run_sh "Write the GPT partition table" \
    "printf '%s\\n' '$script' | sfdisk --quiet '$img'"
  # conv=notrunc : write into the existing file instead of truncating it
  for n in $IMAGE_PARTITIONS; do
    case $n in
      fsbla*)    run "Write BL2 into partition $n (sector ${p_start[$n]})" \
                   dd if="$BL2_BIN" of="$img" bs=$SECTOR seek="${p_start[$n]}" conv=notrunc status=none ;;
      metadata*) run "Write the FWU metadata into partition $n (sector ${p_start[$n]})" \
                   dd if="$META_BIN" of="$img" bs=$SECTOR seek="${p_start[$n]}" conv=notrunc status=none ;;
      fip*)      run "Write the FIP into partition $n (sector ${p_start[$n]})" \
                   dd if="$FIP_BIN" of="$img" bs=$SECTOR seek="${p_start[$n]}" conv=notrunc status=none ;;
    esac
  done
  # conv=sparse : skip writing blocks of zeros, keeps the file small on disk
  run "Copy the ext4 filesystem into partition rootfs (sector ${p_start[rootfs]})" \
    dd if="$EXT4_IMG" of="$img" bs=$SECTOR seek="${p_start[rootfs]}" conv=notrunc,sparse status=none

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
