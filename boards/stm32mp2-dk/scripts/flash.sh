#!/usr/bin/env bash
# =============================================================================
#  scripts/flash.sh - write the build results to a real SD card (needs sudo)
# =============================================================================
#
#  Modes:
#    (default)          write the whole sdcard.img      (erases the card), then erase the
#                       U-Boot environment partition (see "Why the environment is erased")
#    --firmware-only    rewrite only BL2 (fsbla1, fsbla2), the FIP (fip, or fip-a and fip-b)
#                       and, with STACK=st, the FWU metadata; keeps the rest
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
#  Why the environment is erased: bmaptool (and dd with a sparse image) skips blocks that
#  are all zero, so the empty u-boot-env partition of the image is never written. On a card
#  that held another image before (ST's, an older build of this one), U-Boot's saved
#  variables from that image would survive the flash and be loaded at the first boot. The
#  partition is therefore overwritten with zeros after every full write. STACK=st reads the
#  card's partition table, so both stacks use the same code.
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

# The partitions image.sh writes, in table order: IMAGE_PARTITIONS (docs/06-sdcard-image.md).
# part_index <name> = its number in the table (rootfs is 5 on the mainline stack, 8 with STACK=st).
part_index() {
  local i=0 n
  for n in $IMAGE_PARTITIONS; do
    i=$((i + 1))
    [[ $n == "$1" ]] && { echo "$i"; return 0; }
  done
  die "no partition named '$1' in IMAGE_PARTITIONS ($IMAGE_PARTITIONS)"
}

# Refuse to write into a card whose partition table is not ours: the names, in order, must be
# the ones this stack's image has. Read from the table itself (sfdisk), so it works without udev.
check_layout() {
  local got
  got=$(sudo sfdisk --dump "$DEVICE" | sed -n 's/.*name="\([^"]*\)".*/\1/p' | tr '\n' ' ')
  got=${got% }
  [[ $got == "$IMAGE_PARTITIONS" ]] ||
    die "the partitions of $DEVICE are '${got:-<none>}', but the $STACK stack writes '$IMAGE_PARTITIONS': this card was not written by this build (flash the whole image first)"
}

list_candidates() {
  echo "Removable / USB / MMC disks on this machine:"
  lsblk -dpno NAME,SIZE,RM,TRAN,MODEL | awk '$3==1 || $4=="usb" || $1 ~ /mmcblk/ {print "  "$0}'
}

check_device() {
  # A dry run on a PC with no such disk (CI, documentation) only prints the commands.
  if [[ $DRY_RUN == 1 && -n $DEVICE && ! -b $DEVICE ]]; then
    info "Dry run: $DEVICE is not a block device here; on a real card the disk checks below run first."
    return 0
  fi
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
  img=$(readlink -f "$IMAGE" || echo "$IMAGE")      # (a dry run on a tree that was never built)
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
  erase_environment
  [[ $EXPAND == 1 ]] && expand_rootfs
  return 0
}

# Zero the whole u-boot-env partition (see "Why the environment is erased" above). The
# partition is found by NAME in the table just written, with sfdisk, and written through the
# whole-disk device, so it does not depend on the partition device nodes being there yet.
erase_environment() {
  local start size
  if [[ $DRY_RUN == 1 ]]; then
    start="<start of u-boot-env>"; size="<its size>"
  else
    read -r start size < <(sudo sfdisk --dump "$DEVICE" |
      sed -n 's/.*start= *\([0-9]*\), size= *\([0-9]*\),.*name="u-boot-env".*/\1 \2/p')
    [[ -n ${start:-} && -n ${size:-} ]] || die "no partition named u-boot-env on $DEVICE after writing the image"
  fi
  run "Erase the U-Boot environment partition (bmaptool skips zero blocks, so a stale environment would survive)" \
    sudo dd if=/dev/zero of="$DEVICE" bs=512 seek="$start" count="$size" conv=fsync status=none
}

expand_rootfs() {
  local n pr uuid_before="" attrs_before=""
  n=$(part_index rootfs); pr=$(part_of "$DEVICE" "$n")
  section "Growing the rootfs partition to the full size of $DEVICE"
  if [[ $DRY_RUN != 1 ]]; then
    uuid_before=$(sudo sfdisk --part-uuid "$DEVICE" "$n"); attrs_before=$(sudo sfdisk --part-attrs "$DEVICE" "$n")
  fi
  # GPT keeps a backup table at the END of the disk. After writing a small image
  # to a bigger card that backup sits in the middle of the card; sfdisk moves it
  # to the real end when it rewrites the table. ", +" = keep the start sector,
  # size = all remaining space. With -N every other field of the partition (name, type,
  # PARTUUID, attributes) is kept: root=PARTUUID= and U-Boot's "bootable" lookup rely on that.
  run_sh "Grow the rootfs partition to the end of the card" "echo ', +' | sudo sfdisk --quiet --no-reread -N $n '$DEVICE'"
  if [[ $DRY_RUN != 1 ]]; then
    # Checked on util-linux 2.39; verified here so that an sfdisk that behaves differently
    # stops before the card is left with a root= that matches nothing.
    [[ $(sudo sfdisk --part-uuid "$DEVICE" "$n") == "$uuid_before" ]] ||
      die "sfdisk changed the PARTUUID of partition $n: the kernel command line would no longer find the root filesystem"
    [[ $(sudo sfdisk --part-attrs "$DEVICE" "$n") == "$attrs_before" ]] ||
      die "sfdisk dropped the attributes of partition $n: U-Boot would no longer find the bootable partition"
  fi
  run "Re-read the partition table" sudo blockdev --rereadpt "$DEVICE"
  run "Check the filesystem (required before resizing)" sudo e2fsck -fy "$pr"
  run "Grow the ext4 filesystem to fill the partition" sudo resize2fs "$pr"
}

flash_firmware() {
  local bl2 fip meta n
  bl2="$DEPLOY_DIR/tf-a-${TFA_DTB%.dtb}.stm32"
  fip="$DEPLOY_DIR/fip.bin"
  meta="$DEPLOY_DIR/metadata.bin"
  need_file "$bl2" "$fip"
  [[ -z $METADATA_PARTITIONS ]] || need_file "$meta"
  check_device "BL2, the FIP${METADATA_PARTITIONS:+ and the FWU metadata} partitions are overwritten; everything else stays."
  [[ $DRY_RUN == 1 ]] || check_layout
  unmount_all
  # conv=fsync: flush to the card before dd reports success
  for n in fsbla1 fsbla2; do
    run "Write BL2 into $n" sudo dd if="$bl2" of="$(part_of "$DEVICE" "$(part_index "$n")")" bs=64K conv=fsync status=none
  done
  for n in $METADATA_PARTITIONS; do
    run "Write the FWU metadata into $n" sudo dd if="$meta" of="$(part_of "$DEVICE" "$(part_index "$n")")" bs=64K conv=fsync status=none
  done
  for n in $FIP_PARTITIONS; do
    run "Write the FIP into $n" sudo dd if="$fip" of="$(part_of "$DEVICE" "$(part_index "$n")")" bs=64K conv=fsync status=none
  done
}

flash_kernel() {
  local tarball pr mnt
  tarball=$(readlink -f "$DEPLOY_DIR/kernel.tar.gz" || echo "$DEPLOY_DIR/kernel.tar.gz")
  need_file "$tarball"
  check_device "Kernel, device tree and modules in the rootfs partition are replaced."
  [[ $DRY_RUN == 1 ]] || check_layout
  pr=$(part_of "$DEVICE" "$(part_index rootfs)")
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
  section "Flashing ($MODE, $STACK stack) to ${DEVICE:-?}"
  case $MODE in
    image)      flash_image ;;
    firmware)   flash_firmware ;;
    kernel)     flash_kernel ;;
  esac
  run "Make sure every write reached the card" sync
  info "Done. You can remove the card. Boot it on the board with the boot-mode switches set to SD (docs/07-flashing-and-booting.md)."
}

# (also sourceable: the functions can be tested one by one, see docs/07-flashing-and-booting.md)
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main; fi
