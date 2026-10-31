#!/usr/bin/env bash
# =============================================================================
#  tools/flash-sd.sh - write a downloaded boot image (.img.xz or .img) to an SD card
# =============================================================================
#
#  Standalone: copy this one file anywhere. Linux and macOS (bash 3.2 or newer).
#  Needs: xz (for .xz images), dd, and sudo for the write itself. Optional: bmaptool, pv.
#
#  What it does, in this order:
#    1. checks the image against SHA256SUMS (given with -s, or found next to the image)
#    2. lists the removable / external disks (Linux: lsblk, macOS: diskutil list external physical)
#    3. refuses system disks, internal disks and any disk with a filesystem mounted at / (or /boot, /home, ...)
#    4. shows model and size and makes you TYPE the device name
#    5. unmounts it, streams  xz -dc | dd  (or bmaptool copy when installed and a .bmap sits next to the image)
#    6. syncs, then ejects / unmounts; with --verify it reads the card back and compares a hash
#
#  Usage:
#    tools/flash-sd.sh [options] IMAGE
#    tools/flash-sd.sh --list
#
#  Options:
#    -d, --device DEV    the whole disk to write (/dev/sdX, /dev/diskN). Default: choose from the list
#    -s, --sums FILE     SHA256SUMS to check IMAGE against (default: SHA256SUMS next to IMAGE, if any)
#        --verify        after writing, read the card back and compare its sha256 with the image
#        --no-bmap       do not use bmaptool even if installed
#        --list          only list the candidate disks and exit
#    -n, --dry-run       show every step and command, change nothing
#        --allow-file F  TEST MODE: write to the regular file F instead of a disk (no root, no unmount)
#        --allow-internal  Linux: accept a non-removable disk such as /dev/mmcblk0 (still refuses the system disk)
#        --allow-large   accept a disk larger than 256 GB (default refuses: it is probably not an SD card)
#    -h, --help
#
#  Exit status: 0 done (or --list / --dry-run finished), 1 refused or failed, 2 usage error.
# =============================================================================
set -Eeuo pipefail

MAX_GB=256
OS=$(uname -s)

die() { echo "flash-sd: error: $*" >&2; exit 1; }
warn() { echo "flash-sd: warning: $*" >&2; }
say() { echo "flash-sd: $*"; }
usage() { sed -n '/^#  Usage:/,/^#  Exit status/p' "${BASH_SOURCE[0]}" | sed 's/^#//; s/^  //'; }

DRY=0 VERIFY=0 NO_BMAP=0 LIST=0 ALLOW_INTERNAL=0 ALLOW_LARGE=0
DEVICE="" SUMS="" IMAGE="" ALLOW_FILE=""

# Run a command as root unless we already are, or we are in test mode writing to a plain file.
as_root() {
  if [[ $DRY == 1 ]]; then echo "  + $*"; return 0; fi
  if [[ $(id -u) -eq 0 || -n $ALLOW_FILE ]]; then "$@"; else sudo "$@"; fi
}

sha256_stdin() { if command -v sha256sum >/dev/null 2>&1; then sha256sum | cut -d' ' -f1; else shasum -a 256 | cut -d' ' -f1; fi; }

human() { # bytes -> "29.7 GiB"
  awk -v b="$1" 'BEGIN { s = split("B KiB MiB GiB TiB", u, " "); i = 1; while (b >= 1024 && i < s) { b /= 1024; i++ } printf (i == 1 ? "%d %s" : "%.1f %s"), b, u[i] }'
}

# ---------------------------------------------------------------------------
# Linux
# ---------------------------------------------------------------------------
lsblk_field() { # <line from lsblk -P> <KEY>
  if [[ $1 =~ (^|[[:space:]])$2=\"([^\"]*)\" ]]; then echo "${BASH_REMATCH[2]}"; fi
}

# Whole disks that hold the running system: whatever is mounted at / or another system path.
linux_system_disks() {
  local mp src
  for mp in / /boot /boot/efi /home /usr /var /etc /opt /srv /nix; do
    src=$(findmnt -n -o SOURCE --mountpoint "$mp" 2>/dev/null || true)
    [[ -n $src && -e $src ]] || continue
    lsblk -nsrpo NAME,TYPE "$src" 2>/dev/null | awk '$2 == "disk" {print $1}'
  done | sort -u
}

linux_is_system_disk() { linux_system_disks | grep -qx -- "$1"; }

# One tab-separated line per candidate: device, size in bytes, description
linux_candidates() {
  local line name size rm hp tran type model vendor
  lsblk -dnbpP -o NAME,SIZE,RM,HOTPLUG,TRAN,TYPE,MODEL,VENDOR 2>/dev/null | while IFS= read -r line; do
    name=$(lsblk_field "$line" NAME); size=$(lsblk_field "$line" SIZE); rm=$(lsblk_field "$line" RM)
    hp=$(lsblk_field "$line" HOTPLUG); tran=$(lsblk_field "$line" TRAN); type=$(lsblk_field "$line" TYPE)
    model=$(lsblk_field "$line" MODEL); vendor=$(lsblk_field "$line" VENDOR)
    [[ $type == disk ]] || continue
    [[ $rm == 1 || $hp == 1 || $tran == usb ]] || continue
    [[ $size -gt 0 ]] || continue   # an empty card reader slot
    [[ $size -le $((MAX_GB * 1000000000)) || $ALLOW_LARGE == 1 ]] || continue   # too big for an SD card
    linux_is_system_disk "$name" && continue
    printf '%s\t%s\t%s %s %s\n' "$name" "$size" "$vendor" "$model" "${tran:+($tran)}"
  done
}

linux_check_device() { # device: refuse or return
  local dev=$1 type size rm hp tran
  [[ -b $dev ]] || die "$dev is not a block device"
  type=$(lsblk -dnro TYPE "$dev" 2>/dev/null || true)
  [[ $type == disk ]] || die "$dev is a '$type', not a whole disk: give the disk (/dev/sdb), not a partition (/dev/sdb1)"
  if linux_is_system_disk "$dev"; then die "$dev holds the running system (a filesystem on it is mounted at / or another system path): refusing"; fi
  rm=$(lsblk -dnro RM "$dev"); hp=$(lsblk -dnro HOTPLUG "$dev"); tran=$(lsblk -dnro TRAN "$dev" 2>/dev/null || true)
  if [[ $rm != 1 && $hp != 1 && $tran != usb && $ALLOW_INTERNAL != 1 ]]; then
    die "$dev is not removable or hot-pluggable (internal disk?). SD cards in a built-in reader are often reported like this: if you are sure, add --allow-internal"
  fi
  size=$(lsblk -dnbo SIZE "$dev")
  if [[ $size -gt $((MAX_GB * 1000000000)) && $ALLOW_LARGE != 1 ]]; then
    die "$dev is $(human "$size"): larger than ${MAX_GB} GB, probably not an SD card. Add --allow-large to override"
  fi
}

linux_describe() { lsblk -dnbo SIZE,VENDOR,MODEL "$1" | awk '{s=$1; $1=""; printf "%s\t%s\n", s, $0}'; }

linux_unmount() {
  local dev=$1 mp
  lsblk -nro MOUNTPOINT "$dev" | while IFS= read -r mp; do
    [[ -n $mp ]] || continue
    case $mp in / | /boot* | /home* | /usr* | /var* | /etc* | /opt* | /srv* | /nix*) die "$dev has $mp mounted: refusing" ;; esac
    say "unmounting $mp"
    as_root umount "$mp"
  done
}

# ---------------------------------------------------------------------------
# macOS
# ---------------------------------------------------------------------------
mac_external_disks() { diskutil list external physical 2>/dev/null | grep -E '^/dev/disk[0-9]+' | awk '{print $1}'; }

mac_info() { diskutil info "$1" 2>/dev/null; }

mac_candidates() {
  local d info bytes name
  for d in $(mac_external_disks); do
    info=$(mac_info "$d")
    echo "$info" | grep -q 'Device Location:[[:space:]]*Internal' && continue
    bytes=$(echo "$info" | sed -n 's/.*Disk Size:.*(\([0-9][0-9]*\) Bytes).*/\1/p' | head -n1)
    name=$(echo "$info" | sed -n 's/^[[:space:]]*Device \/ Media Name:[[:space:]]*//p' | head -n1)
    [[ ${bytes:-0} -gt 0 ]] || continue
    [[ $bytes -le $((MAX_GB * 1000000000)) || $ALLOW_LARGE == 1 ]] || continue
    printf '%s\t%s\t%s\n' "$d" "$bytes" "$name"
  done
}

mac_check_device() {
  local dev=$1 d base info bytes
  base=${dev#/dev/r}; base=${base#/dev/}
  [[ $base =~ ^disk[0-9]+$ ]] || die "$dev is not a whole disk (expected /dev/diskN, not a slice like disk4s1)"
  d=/dev/$base
  mac_external_disks | grep -qx -- "$d" || die "$d is not in 'diskutil list external physical': only external physical disks are accepted"
  info=$(mac_info "$d")
  if echo "$info" | grep -q 'Device Location:[[:space:]]*Internal'; then die "$d is an internal disk: refusing"; fi
  if diskutil info / 2>/dev/null | grep -q "Part of Whole:[[:space:]]*$base\$"; then die "$d holds the running system: refusing"; fi
  bytes=$(echo "$info" | sed -n 's/.*Disk Size:.*(\([0-9][0-9]*\) Bytes).*/\1/p' | head -n1)
  if [[ ${bytes:-0} -gt $((MAX_GB * 1000000000)) && $ALLOW_LARGE != 1 ]]; then
    die "$d is $(human "$bytes"): larger than ${MAX_GB} GB, probably not an SD card. Add --allow-large to override"
  fi
}

# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------
candidates() { if [[ $OS == Darwin ]]; then mac_candidates; else linux_candidates; fi; }

print_candidates() {
  local n=0 dev size desc
  while IFS=$'\t' read -r dev size desc; do
    printf '  %-14s %10s   %s\n' "$dev" "$(human "$size")" "$desc"
    n=$((n + 1))
  done < <(candidates)
  [[ $n -gt 0 ]] || echo "  (no removable or external disks found: insert the card, or use a USB card reader)"
  return 0
}

raw_size_of() { # uncompressed size of IMAGE in bytes
  case $IMAGE in
    *.xz) xz --robot --list "$IMAGE" | awk '$1 == "totals" {print $5}' ;;
    *)    wc -c <"$IMAGE" | tr -d ' ' ;;
  esac
}

stream_image() { case $IMAGE in *.xz) xz -dc "$IMAGE" ;; *) cat "$IMAGE" ;; esac; }

check_checksum() {
  local base want got explicit=0
  base=$(basename "$IMAGE")
  if [[ -n $SUMS ]]; then explicit=1; else
    [[ -f $(dirname "$IMAGE")/SHA256SUMS ]] && SUMS=$(dirname "$IMAGE")/SHA256SUMS
  fi
  if [[ -z $SUMS ]]; then warn "no SHA256SUMS given or found next to the image: the download is NOT checked"; return 0; fi
  [[ -f $SUMS ]] || die "$SUMS not found"
  want=$(awk -v f="$base" '{n = $2; sub(/^\*/, "", n); if (n == f) print $1}' "$SUMS" | head -n1)
  if [[ -z $want ]]; then
    if [[ $explicit == 1 ]]; then die "$base is not listed in $SUMS"; fi
    warn "$base is not listed in $SUMS: the download is NOT checked"; return 0
  fi
  say "checking sha256 of $base ..."
  got=$(sha256_stdin <"$IMAGE")
  [[ $got == "$want" ]] || die "checksum mismatch for $base (file $got, $SUMS says $want). Download it again."
  say "checksum ok"
}

pick_device() {
  local list=() dev size desc i=1 choice
  while IFS=$'\t' read -r dev size desc; do list[${#list[@]}]="$dev"; printf '  %d) %-14s %10s   %s\n' "$i" "$dev" "$(human "$size")" "$desc"; i=$((i + 1)); done < <(candidates)
  [[ ${#list[@]} -gt 0 ]] || die "no removable or external disk found: insert the card (a USB card reader is the most reliable), or pass --device"
  if [[ ${#list[@]} -eq 1 ]]; then DEVICE=${list[0]}; say "only one candidate: $DEVICE"; return 0; fi
  printf 'Number of the disk to write: '
  read -r choice
  [[ $choice =~ ^[0-9]+$ && $choice -ge 1 && $choice -le ${#list[@]} ]] || die "not a valid choice"
  DEVICE=${list[$((choice - 1))]}
}

main() {
  local arg
  while [[ $# -gt 0 ]]; do
    arg=$1
    case $arg in
      -d | --device) [[ $# -ge 2 ]] || { echo "flash-sd: $arg needs a value" >&2; exit 2; }; DEVICE=$2; shift ;;
      -s | --sums) [[ $# -ge 2 ]] || { echo "flash-sd: $arg needs a value" >&2; exit 2; }; SUMS=$2; shift ;;
      --allow-file) [[ $# -ge 2 ]] || { echo "flash-sd: $arg needs a value" >&2; exit 2; }; ALLOW_FILE=$2; shift ;;
      --verify) VERIFY=1 ;;
      --no-bmap) NO_BMAP=1 ;;
      --list) LIST=1 ;;
      -n | --dry-run) DRY=1 ;;
      --allow-internal) ALLOW_INTERNAL=1 ;;
      --allow-large) ALLOW_LARGE=1 ;;
      -h | --help) usage; exit 0 ;;
      -*) echo "flash-sd: unknown option $arg" >&2; usage >&2; exit 2 ;;
      *) [[ -z $IMAGE ]] || { echo "flash-sd: only one image, please" >&2; exit 2; }; IMAGE=$arg ;;
    esac
    shift
  done

  if [[ $LIST == 1 ]]; then
    echo "Removable / external disks:"
    print_candidates
    exit 0
  fi
  [[ -n $IMAGE ]] || { usage >&2; exit 2; }
  [[ -f $IMAGE ]] || die "image $IMAGE not found"
  case $IMAGE in *.xz) command -v xz >/dev/null 2>&1 || die "xz is needed for .xz images (Linux: apt install xz-utils, macOS: brew install xz)" ;; esac

  local raw bs dd_progress="" target bmap="" name size desc typed expect
  say "image: $(basename "$IMAGE")"
  check_checksum
  raw=$(raw_size_of 2>/dev/null || true)
  [[ $raw =~ ^[0-9]+$ && $raw -gt 0 ]] || die "cannot read the size of $IMAGE: is it a valid .xz file?"
  say "$(human "$raw") when unpacked"

  # ---- choose and check the target ----
  if [[ -n $ALLOW_FILE ]]; then
    target=$ALLOW_FILE
    [[ ! -e $target || -f $target ]] || die "--allow-file wants a regular file, not $target"
    size=$raw; desc="regular file (test mode)"; expect=$(basename "$target")
    warn "TEST MODE: writing to the plain file $target, not to a disk"
  else
    [[ $OS == Linux || $OS == Darwin ]] || die "unsupported OS $OS: on Windows use Raspberry Pi Imager or balenaEtcher (see docs/downloads.md)"
    if [[ -z $DEVICE ]]; then
      echo "Removable / external disks:"
      pick_device
    fi
    if [[ $OS == Darwin ]]; then
      mac_check_device "$DEVICE"
      DEVICE=/dev/${DEVICE#/dev/r}; DEVICE=/dev/${DEVICE#/dev/}
      expect=${DEVICE#/dev/}
      target=/dev/r$expect
      size=$(mac_info "$DEVICE" | sed -n 's/.*Disk Size:.*(\([0-9][0-9]*\) Bytes).*/\1/p' | head -n1)
      desc=$(mac_info "$DEVICE" | sed -n 's/^[[:space:]]*Device \/ Media Name:[[:space:]]*//p' | head -n1)
      bs=4m
    else
      linux_check_device "$DEVICE"
      target=$DEVICE; expect=${DEVICE#/dev/}
      IFS=$'\t' read -r size desc < <(linux_describe "$DEVICE")
      bs=4M; dd_progress="status=progress"
    fi
    [[ $size -ge $raw ]] || die "the image ($(human "$raw")) does not fit on $DEVICE ($(human "$size"))"
  fi
  bs=${bs:-4M}

  # ---- confirm ----
  echo
  echo "  About to ERASE and overwrite:  ${DEVICE:-$target}"
  echo "  Model / description:           ${desc:-unknown}"
  echo "  Size:                          $(human "$size")"
  echo "  Image:                         $(basename "$IMAGE")  ($(human "$raw") unpacked)"
  echo
  if [[ $DRY == 1 ]]; then
    say "dry run: nothing is asked and nothing is written. The commands would be:"
  else
    printf 'Everything on it will be lost. Type the device name (%s) to confirm: ' "$expect"
    read -r typed
    [[ $typed == "$expect" ]] || die "you typed '$typed', not '$expect': nothing was written"
  fi

  # ---- unmount ----
  if [[ -z $ALLOW_FILE ]]; then
    if [[ $OS == Darwin ]]; then as_root diskutil unmountDisk "$DEVICE"; elif [[ $DRY == 1 ]]; then echo "  + umount every mounted partition of $DEVICE"; else linux_unmount "$DEVICE"; fi
  fi

  # ---- write ----
  local base_img=${IMAGE%.xz}
  [[ $NO_BMAP == 1 ]] || for bmap in "$IMAGE.bmap" "$base_img.bmap"; do [[ -f $bmap ]] && break; bmap=""; done
  if [[ -n $bmap ]] && command -v bmaptool >/dev/null 2>&1; then
    say "writing with bmaptool (only the used blocks) using $(basename "$bmap")"
    # bmaptool skips blocks the image does not map, so whatever a previous use left in the gap before the
    # first partition (a saved U-Boot environment, an old boot loader) would survive. Clear the first 16 MiB.
    if [[ -z $ALLOW_FILE ]]; then
      say "clearing the first 16 MiB of the card (stale boot loader or U-Boot environment)"
      if [[ $OS == Darwin ]]; then as_root dd if=/dev/zero of="$target" bs=1m count=16; else as_root dd if=/dev/zero of="$target" bs=1M count=16 conv=fsync status=none; fi
    fi
    if [[ $DRY == 1 ]]; then echo "  + bmaptool copy --bmap $bmap $IMAGE $target"; else as_root bmaptool copy --bmap "$bmap" "$IMAGE" "$target"; fi
  else
    [[ -z $bmap ]] || say "a .bmap is next to the image but bmaptool is not installed: writing everything with dd (pip install bmaptool, or apt install bmap-tools, to skip the empty space)"
    say "writing $(human "$raw") to $target ..."
    # macOS dd has no conv=fsync or status=: the explicit sync below covers it
    local ddargs=(of="$target" bs="$bs")
    if [[ $OS == Linux ]]; then ddargs=(of="$target" bs="$bs" conv=fsync iflag=fullblock); [[ -z $dd_progress ]] || ddargs[${#ddargs[@]}]=$dd_progress; fi
    [[ $OS != Darwin ]] || say "macOS dd prints no progress by itself: press Ctrl-T to see it"
    if [[ $DRY == 1 ]]; then
      echo "  + $(case $IMAGE in *.xz) echo "xz -dc $IMAGE" ;; *) echo "cat $IMAGE" ;; esac) | dd ${ddargs[*]}"
    elif command -v pv >/dev/null 2>&1; then
      stream_image | pv -s "$raw" | as_root dd "${ddargs[@]/status=progress/status=none}"
    else
      stream_image | as_root dd "${ddargs[@]}"
    fi
  fi

  say "syncing ..."
  if [[ $DRY == 1 ]]; then echo "  + sync"; else sync; fi

  # ---- verify ----
  if [[ $VERIFY == 1 ]]; then
    say "reading back $(human "$raw") to compare ..."
    if [[ $DRY == 1 ]]; then
      echo "  + dd if=$target bs=$bs | head -c $raw | sha256"
    else
      local want got
      want=$(stream_image | sha256_stdin)
      got=$(as_root dd if="$target" bs="$bs" 2>/dev/null | head -c "$raw" | sha256_stdin) || true
      [[ $got == "$want" ]] || die "VERIFY FAILED: the card holds $got, the image is $want. Try another card or reader."
      say "verify ok (sha256 ${want:0:16}...)"
    fi
  fi

  # ---- eject ----
  if [[ -z $ALLOW_FILE ]]; then
    if [[ $OS == Darwin ]]; then
      as_root diskutil eject "$DEVICE"
    elif command -v eject >/dev/null 2>&1; then
      as_root eject "$DEVICE" || warn "could not eject $DEVICE: wait until the activity LED stops before removing the card"
    else
      say "no 'eject' command: the data is synced; wait until the reader's LED stops before removing the card"
    fi
  fi
  say "done. Put the card in the board, set the boot switch to SD, open the serial console, power on."
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi
