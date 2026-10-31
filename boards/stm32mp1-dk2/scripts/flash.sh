#!/usr/bin/env bash
# =============================================================================
#  scripts/flash.sh - write the build results to a real SD card (needs sudo)
# =============================================================================
#
#  Modes:
#    (default)          write the whole sdcard.img      (erases the card)
#    --firmware-only    rewrite only BL2 (fsbl1, fsbl2) and the FIP (keeps the rest)
#    --kernel-only      copy kernel/dtb/modules into the rootfs partition (keeps everything else)
#
#  Options:
#    -d, --device /dev/sdX   the SD card (WHOLE disk, not a partition)
#    --image FILE            image to write (default build/deploy/sdcard.img)
#    --expand                after writing, grow the rootfs partition to fill the card
#    --force                 allow non-removable / large disks (be careful!)
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
P_FSBL1=1; P_FSBL2=2; P_FIP=3; P_ROOTFS=5

# Refuse to write into a card whose partition table is not ours.
check_layout() {
  local want=(fsbl1 fsbl2 fip u-boot-env rootfs) i got
  for i in 1 2 3 4 5; do
    got=$(lsblk -no PARTLABEL "$(part_of "$DEVICE" "$i")" 2>/dev/null | head -n1 | tr -d ' ')
    [[ $got == "${want[i-1]}" ]] ||
      die "partition $i of $DEVICE is named '${got:-<none>}', expected '${want[i-1]}': this card was not written by this build (flash the whole image first)"
  done
}

list_candidates() {
  echo "Removable / USB / MMC disks on this machine:"
  lsblk -dpno NAME,SIZE,RM,TRAN,MODEL | awk '$3==1 || $4=="usb" || $1 ~ /mmcblk/ {print "  "$0}'
}

check_device() {
  [[ -n $DEVICE ]] || { list_candidates; die "no device given: use -d /dev/sdX"; }
  [[ -b $DEVICE ]] || { list_candidates; die "$DEVICE is not a block device"; }
  [[ $(lsblk -dno TYPE "$DEVICE") == disk ]] || die "$DEVICE is not a whole disk (give /dev/sdX, not /dev/sdX1)"

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
  # bmaptool skips blocks of zeros, so an old U-Boot environment on a reused card would
  # survive the write. Wipe the whole u-boot-env partition (offset and size from the config).
  run "Erase the U-Boot environment partition (stale variables from an earlier image)" \
    sudo dd if=/dev/zero of="$DEVICE" bs=1K seek=$(( ENV_START_MB * 1024 )) count="$ENV_SIZE_KB" conv=fsync status=none
  run "Ask the kernel to re-read the new partition table" sudo blockdev --rereadpt "$DEVICE"
  [[ $EXPAND == 1 ]] && expand_rootfs
  return 0
}

expand_rootfs() {
  local pr; pr=$(part_of "$DEVICE" "$P_ROOTFS")
  section "Growing the rootfs partition to the full size of $DEVICE"
  # GPT keeps a backup table at the END of the disk. After writing a small image
  # to a bigger card that backup sits in the middle of the card; sfdisk moves it
  # to the real end when it rewrites the table. ", +" = keep the start sector,
  # size = all remaining space.
  run_sh "Grow the rootfs partition to the end of the card" "echo ', +' | sudo sfdisk --quiet --no-reread -N $P_ROOTFS '$DEVICE'"
  run "Re-read the partition table" sudo blockdev --rereadpt "$DEVICE"
  run "Check the filesystem (required before resizing)" sudo e2fsck -fy "$pr"
  run "Grow the ext4 filesystem to fill the partition" sudo resize2fs "$pr"
}

flash_firmware() {
  local bl2 fip
  bl2="$DEPLOY_DIR/tf-a-${TFA_DTB%.dtb}.stm32"
  fip="$DEPLOY_DIR/fip.bin"
  need_file "$bl2" "$fip"
  check_device "BL2 and the FIP partitions are overwritten; everything else stays."
  [[ $DRY_RUN == 1 ]] || check_layout
  unmount_all
  # conv=fsync: flush to the card before dd reports success
  run "Write BL2 into fsbl1" sudo dd if="$bl2" of="$(part_of "$DEVICE" $P_FSBL1)" bs=64K conv=fsync status=none
  run "Write the same BL2 into fsbl2 (the ROM's fallback copy)" sudo dd if="$bl2" of="$(part_of "$DEVICE" $P_FSBL2)" bs=64K conv=fsync status=none
  run "Write the FIP into the fip partition" sudo dd if="$fip" of="$(part_of "$DEVICE" $P_FIP)" bs=64K conv=fsync status=none
}

flash_kernel() {
  local tarball pr mnt
  tarball=$(readlink -f "$DEPLOY_DIR/kernel.tar.gz")
  need_file "$tarball"
  check_device "Kernel, device tree and modules in the rootfs partition are replaced."
  [[ $DRY_RUN == 1 ]] || check_layout
  pr=$(part_of "$DEVICE" "$P_ROOTFS")
  unmount_all
  mnt=$(mktemp -d)
  run "Mount the root partition" sudo mount "$pr" "$mnt"
  # Old modules directories of other versions are left alone (harmless).
  run "Unpack kernel, DTB and modules (keep /lib -> usr/lib symlinks intact)" \
    sudo tar -xzf "$tarball" -C "$mnt" --no-same-owner --keep-directory-symlink
  run "Flush writes" sync
  run "Unmount" sudo umount "$mnt"
  rmdir "$mnt" 2>/dev/null || true
}

main() {
  need_cmd lsblk sudo dd
  section "Flashing ($MODE) to ${DEVICE:-?}"
  case $MODE in
    image)      flash_image ;;
    firmware)   flash_firmware ;;
    kernel)     flash_kernel ;;
  esac
  run "Make sure every write reached the card" sync
  info "Done. You can remove the card. Boot it on the board with the boot-mode switches set to SD (docs/07-flashing-and-booting.md)."
}

main
