#!/usr/bin/env bash
# =============================================================================
#  scripts/flash.sh - write the build results to a real SD card (needs sudo)
# =============================================================================
#
#  Modes:
#    (default)          write the whole sdcard.img      (erases the card)
#    --firmware-only    rewrite only BOOT.BIN and u-boot.img on the FAT partition (keeps the rest)
#    --kernel-only      replace zImage + DTB on the FAT partition and the modules in the rootfs
#                       partition (keeps everything else)
#
#  Options:
#    -d, --device /dev/sdX   the SD card (WHOLE disk, not a partition)
#    --image FILE            image to write (default build/deploy/sdcard.img)
#    --expand                after writing, grow the rootfs (partition 2) to fill the card
#    --force                 allow non-removable / large disks and loop devices (be careful!)
#    -y, --yes               do not ask for confirmation
#    -n, --dry-run           print the commands only
#
#  Safety checks before anything is written:
#    - target must be a whole block device (not /dev/sdb1)
#    - it must not hold a mounted system filesystem (/, /boot, /home, ...)
#    - it must be removable or attached via USB/MMC, and <= 256 GB,
#      unless --force is given
#    - you confirm after seeing its model and size
# =============================================================================
# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
strict_mode
load_config

DEVICE=""
MODE=image
IMAGE="$DEPLOY_DIR/sdcard.img"
EXPAND=0
FORCE=0
MAX_SIZE_GB=256

usage() { sed -n '/^#  Modes:/,/^# ====/p' "$0" | sed 's/^# \{0,1\}//; /^====/d'; exit "${1:-0}"; }

while (($#)); do
  case $1 in
    -d|--device)       DEVICE=$2; shift ;;
    --image)           IMAGE=$2; shift ;;
    --firmware-only)   MODE=firmware ;;
    --kernel-only)     MODE=kernel ;;
    --expand)          EXPAND=1 ;;
    --force)           FORCE=1 ;;
    -y|--yes)          ASSUME_YES=1 ;;
    -n|--dry-run)      DRY_RUN=1 ;;
    -h|--help)         usage 0 ;;
    *) warn "unknown option $1"; usage 1 ;;
  esac
  shift
done

# /dev/sdb -> /dev/sdb1, /dev/mmcblk0 -> /dev/mmcblk0p1, /dev/loop0 -> /dev/loop0p1
part_of() { [[ $1 =~ [0-9]$ ]] && echo "${1}p$2" || echo "${1}$2"; }

# Partition numbers of the layout image.sh writes (docs/06-sdcard-image.md)
P_BOOT=1; P_ROOTFS=2

# Refuse to write into a card whose layout is not ours. An MBR has no partition names,
# so the file system labels are the check: BOOT (FAT) and rootfs (ext4).
check_layout() {
  local want_fs=(vfat ext4) want_label=("$BOOT_LABEL" "$ROOTFS_LABEL") i fs label
  for i in 1 2; do
    # blkid (as root) probes the partition itself; lsblk would depend on udev's database
    fs=$(sudo blkid -o value -s TYPE "$(part_of "$DEVICE" "$i")" 2>/dev/null) || fs=
    label=$(sudo blkid -o value -s LABEL "$(part_of "$DEVICE" "$i")" 2>/dev/null) || label=
    [[ $fs == "${want_fs[i-1]}" && $label == "${want_label[i-1]}" ]] ||
      die "partition $i of $DEVICE is '${fs:-<none>}' labelled '${label:-<none>}', expected '${want_fs[i-1]}' labelled '${want_label[i-1]}': this card was not written by this build (flash the whole image first)"
  done
}

list_candidates() {
  echo "Removable / USB / MMC disks on this machine:"
  lsblk -dpno NAME,SIZE,RM,TRAN,MODEL | awk '$3==1 || $4=="usb" || $1 ~ /mmcblk/ {print "  "$0}'
}

check_device() {
  [[ -n $DEVICE ]] || { list_candidates; die "no device given: use -d /dev/sdX"; }
  if [[ $DRY_RUN == 1 ]]; then
    explain "(dry run) the real run checks that $DEVICE is a whole removable disk, not mounted as a system path," \
            "at most ${MAX_SIZE_GB} GB, shows its model and size, and asks you to confirm."
    return 0
  fi
  [[ -b $DEVICE ]] || { list_candidates; die "$DEVICE is not a block device"; }
  local type; type=$(lsblk -dno TYPE "$DEVICE")
  # A loop device (an image attached with losetup) is accepted only with --force: handy for testing.
  [[ $type == disk || ( $type == loop && $FORCE == 1 ) ]] || die "$DEVICE is not a whole disk (give /dev/sdX, not /dev/sdX1)"

  # Refuse if any partition of the device is mounted on a system path.
  local mp
  while read -r mp; do
    case $mp in
      /|/boot|/boot/efi|/home|/usr|/var|"[SWAP]") die "$DEVICE holds a system mount ($mp) - this is NOT your SD card!" ;;
    esac
  done < <(lsblk -lnpo MOUNTPOINT "$DEVICE" | sed '/^$/d')

  local rm tran size_b model
  rm=$(lsblk -dno RM "$DEVICE" | tr -d ' ')
  tran=$(lsblk -dno TRAN "$DEVICE" | tr -d ' ')
  size_b=$(lsblk -bdno SIZE "$DEVICE" | tr -d ' ')
  model=$(lsblk -dno MODEL "$DEVICE" | sed 's/ *$//')
  if [[ $FORCE != 1 ]]; then
    [[ $rm == 1 || $tran == usb || $DEVICE == /dev/mmcblk* ]] ||
      die "$DEVICE ($model) is neither removable nor USB/MMC; use --force if you are SURE"
    (( size_b <= MAX_SIZE_GB * 1000**3 )) ||
      die "$DEVICE is larger than ${MAX_SIZE_GB} GB - unusual for an SD card; use --force if you are SURE"
  fi

  echo
  lsblk -po NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINT "$DEVICE" | sed 's/^/  /'
  echo
  confirm "Write to $DEVICE (${model:-unknown model}, $((size_b / 1000**3)) GB)? $1" || die "aborted by user"
}

unmount_all() {
  local p
  for p in $(lsblk -lnpo NAME "$DEVICE" | tail -n +2); do
    if findmnt -rno TARGET "$p" >/dev/null; then
      run "Unmount $p (desktop auto-mounted it)" sudo umount "$p"
    fi
  done
}

flash_image() {
  local img
  img=$(readlink -f "$IMAGE")
  need_file "$img"
  check_device "ALL DATA ON IT WILL BE LOST."
  unmount_all
  if [[ -f $img.bmap ]] && command -v bmaptool >/dev/null; then
    # bmaptool writes only the blocks that hold data and verifies checksums
    run "Write the image (only used blocks, verified)" sudo bmaptool copy --bmap "$img.bmap" "$img" "$DEVICE"
  else
    # bs=4M        : large blocks = fast
    # conv=fsync   : flush to the card before dd reports success
    # status=progress : live progress
    run "Write the image byte for byte" sudo dd if="$img" of="$DEVICE" bs=4M conv=fsync status=progress
  fi
  run "Ask the kernel to re-read the new partition table" sudo blockdev --rereadpt "$DEVICE"
  [[ $EXPAND == 1 ]] && expand_rootfs
  return 0
}

expand_rootfs() {
  local pr; pr=$(part_of "$DEVICE" "$P_ROOTFS")
  section "Growing the rootfs partition to the full size of $DEVICE"
  # ", +" = keep the start sector, size = all remaining space. (An MBR keeps no backup
  # table at the end of the disk, unlike a GPT, so the card's extra space is simply unused
  # until now.)
  run_sh "Grow the rootfs partition to the end of the card" "echo ', +' | sudo sfdisk --quiet --no-reread -N $P_ROOTFS '$DEVICE'"
  run "Re-read the partition table" sudo blockdev --rereadpt "$DEVICE"
  run "Check the filesystem (required before resizing)" sudo e2fsck -fy "$pr"
  run "Grow the ext4 filesystem to fill the partition" sudo resize2fs "$pr"
}

flash_firmware() {
  local pb
  need_cmd mcopy mdir
  need_file "$DEPLOY_DIR/BOOT.BIN" "$DEPLOY_DIR/u-boot.img"
  check_device "BOOT.BIN and u-boot.img on the FAT partition are replaced; everything else stays."
  [[ $DRY_RUN == 1 ]] || check_layout
  pb=$(part_of "$DEVICE" $P_BOOT)
  unmount_all
  # mtools can write a FAT file system on a block device directly: no mount needed.
  # -o overwrites without asking.
  run "Write BOOT.BIN (what the BootROM loads)" sudo mcopy -o -i "$pb" "$DEPLOY_DIR/BOOT.BIN" ::BOOT.BIN
  run "Write u-boot.img (what the SPL loads)" sudo mcopy -o -i "$pb" "$DEPLOY_DIR/u-boot.img" ::u-boot.img
}

flash_kernel() {
  local overlay pb pr mnt
  need_cmd mcopy
  overlay="$DEPLOY_DIR/kernel"
  need_file "$overlay/fat/$KERNEL_IMAGE"
  check_device "zImage and the device tree (FAT) and the modules (rootfs) are replaced."
  [[ $DRY_RUN == 1 ]] || check_layout
  pb=$(part_of "$DEVICE" $P_BOOT)
  pr=$(part_of "$DEVICE" $P_ROOTFS)
  unmount_all
  run "Write the kernel image into the FAT partition" sudo mcopy -o -i "$pb" "$overlay/fat/$KERNEL_IMAGE" "::$KERNEL_IMAGE"
  local d
  for d in "$overlay"/fat/*.dtb; do
    run "Write $(basename "$d") into the FAT partition" sudo mcopy -o -i "$pb" "$d" "::$(basename "$d")"
  done
  mnt=$(mktemp -d)
  run "Mount the root partition" sudo mount "$pr" "$mnt"
  # Old modules directories of other versions are left alone (harmless).
  run_sh "Unpack modules and kernel config (keep /lib -> usr/lib symlinks intact)" \
    "tar -C '$overlay/rootfs' -cf - . | sudo tar -xf - -C '$mnt' --no-same-owner --keep-directory-symlink"
  run "Flush writes" sync
  run "Unmount" sudo umount "$mnt"
  rmdir "$mnt" 2>/dev/null || true
}

main() {
  need_cmd lsblk sudo dd blkid
  section "Flashing ($MODE) to ${DEVICE:-?}"
  case $MODE in
    image)      flash_image ;;
    firmware)   flash_firmware ;;
    kernel)     flash_kernel ;;
  esac
  run "Make sure every write reached the card" sync
  info "Done. You can remove the card. Boot it on the board with the boot-mode jumper JP5 on SD (docs/07-flashing-and-booting.md)."
}

main
