#!/usr/bin/env bash
# =============================================================================
#  scripts/uuu.sh - run the build from RAM, or flash the on-module eMMC, over USB
# =============================================================================
#
#  The i.MX8M Plus Boot ROM has a mode of its own, "serial download": it does
#  not read any storage, it waits on the USB OTG port for a host to send it a
#  bootloader. NXP's `uuu` (Universal Update Utility) is that host. This script
#  drives it with small, generated, commented .uuu scripts:
#
#    uuu deps             fetch the pinned uuu (sha256-checked) into build/tools/
#    uuu udev             install the udev rule that lets you run uuu without sudo
#    uuu check            what does the PC see on USB right now?
#    uuu spl              Boot ROM -> SPL -> U-Boot from RAM, then stop in fastboot
#    uuu boot             ... then load kernel + device tree + root filesystem into
#                         RAM and start Linux. Nothing is written to any storage
#    uuu emmc             ... then write the eMMC: user area + boot partitions
#          [--rootfs-only]      only partition 1 (the root filesystem)
#          [--bootloader-only]  only imx-boot into boot0/boot1 + the ROM boot config
#
#  Common options:  --no-spl   U-Boot is already running in fastboot (a previous
#                              `uuu spl`); skip the ROM phase
#                   --sudo     run uuu through sudo (instead of the udev rule)
#                   -y/-n      as in build.sh (no prompts / explain only)
#
#  Everything is rootless on the PC except what the USB device permissions need.
#  Why each step exists, with the sources it comes from: docs/16-booting-from-emmc-with-uuu.md
# =============================================================================
# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
strict_mode
load_config

UUU_TPL="$TOP_DIR/scripts/uuu"
UUU_TOOLS="$BUILD_DIR/tools"
UUU_BIN="${UUU_BIN:-$UUU_TOOLS/uuu-$UUU_VERSION}"
RAM_DIR="$DEPLOY_DIR/uuu-ram"

BOOT_BIN="$DEPLOY_DIR/imx-boot.bin"
USE_SUDO=0
NO_SPL=0
EMMC_MODE=full
DTB="$UUU_DTB"
CONSOLE="$UUU_CONSOLE"

usage() { sed -n '/^#  The i.MX8M Plus Boot ROM/,/^# ====/p' "$0" | sed 's/^# \{0,2\}//; /^====/d'; exit "${1:-0}"; }

# -----------------------------------------------------------------------------
# Small helpers
# -----------------------------------------------------------------------------
hex() { printf '0x%x' "$1"; }

# USB IDs on the PC (vendor:product, lower case), one per line.
usb_ids() {
  if command -v lsusb >/dev/null 2>&1; then
    lsusb | awk '{print tolower($6)}'
  else
    "$UUU_BIN" -lsusb 2>/dev/null | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' |
      awk '/0x1fc9/ {for (i = 1; i <= NF; i++) if ($i ~ /^0x1fc9$/) printf "1fc9:%s\n", substr($(i + 1), 3)}'
  fi
}

# rom = serial download mode (1fc9:0146), fastboot = U-Boot's fastboot gadget (1fc9:0152), none
usb_state() {
  local ids
  ids=$(usb_ids || true)
  if grep -qx '1fc9:0146' <<<"$ids"; then echo rom
  elif grep -qx '1fc9:0152' <<<"$ids"; then echo fastboot
  else echo none; fi
}

board_checklist() {
  cat >&2 <<EOF

  The PC does not see the board in serial download mode (USB 1fc9:0146).
  Check, in this order:
    1. the USB cable is in the carrier's USB OTG (download) port, not in a host port or the debug-UART port,
       and goes straight to the PC (no hub or dock: they break the ROM -> U-Boot USB hand-over);
    2. the boot switch is on SD and NO SD card is in the slot (the Boot ROM then falls back to serial
       download), or your carrier's manual says which switch position selects "USB / serial download";
    3. power-cycle the board with the cable already connected;
    4. 'lsusb | grep 1fc9' (or ./build.sh uuu check) shows 1fc9:0146 before you try again.
  More: docs/16-booting-from-emmc-with-uuu.md (troubleshooting table).
EOF
}

uuu_failed_hints() {
  cat >&2 <<EOF

  uuu stopped. The line uuu printed in red above is the cause. The usual ones:
    Failure open usb device,Try sudo uuu      -> USB permissions: ./build.sh uuu udev, or re-run with --sudo
    Timeout: Wait for Known USB Device        -> the board is not in serial download mode (./build.sh uuu check)
    Timeout: Wait for next USB Device         -> the ROM -> U-Boot hand-over failed: connect the PC and the board
                                                 directly (no hub), power-cycle, try 'uuu spl' then 'uuu emmc --no-spl'
    FB: ... fail / Unknown Command            -> read the failing line in build/deploy/*.uuu; docs/16 explains each
  The board is safe to power-cycle: the Boot ROM cannot be overwritten, so USB recovery always works.
EOF
}

resolve_uuu() {
  [[ $DRY_RUN == 1 ]] && return 0
  [[ -x $UUU_BIN ]] || die "uuu not found at $UUU_BIN  ->  run: ./build.sh uuu deps"
}

# Run uuu on a generated script from build/deploy (the scripts name their files without a path).
run_uuu() {
  local script=$1 why=$2
  local cmd=("$UUU_BIN" -t "$UUU_WAIT_FIRST" -T "$UUU_WAIT_NEXT" "$script")
  ((USE_SUDO == 0)) || cmd=(sudo "${cmd[@]}")
  run_cd "uuu looks for the files named in the script in the current directory" "$DEPLOY_DIR"
  printf '%s  # %s%s\n' "$C_DIM" "$why" "$C_RESET"
  printf '%s  $ %s%s\n' "$C_CYAN" "$(short_paths "$(quote_cmd "${cmd[@]}")")" "$C_RESET"
  [[ $DRY_RUN == 1 ]] && return 0
  local rc=0
  "${cmd[@]}" || rc=$?
  ((rc == 0)) || { uuu_failed_hints; die "uuu failed (exit $rc)"; }
}

# -----------------------------------------------------------------------------
# Script generation: concatenate the commented fragments in scripts/uuu/ and
# fill in the real file names and addresses.
#   gen_script <file name> <build.sh sub-command> <fragment>...
# The caller fills the associative array SUBST (placeholder -> value).
# -----------------------------------------------------------------------------
declare -A SUBST=()
gen_script() {
  local name=$1 subcmd=$2; shift 2
  local f s='' key left
  SUBST[NAME]=$name
  SUBST[CMD]=$subcmd
  SUBST[UUU_VERSION]=$UUU_VERSION
  for f in 00-header "$@"; do
    [[ -f $UUU_TPL/$f.uuu.in ]] || die "missing template $UUU_TPL/$f.uuu.in"
    s+=$(cat "$UUU_TPL/$f.uuu.in")$'\n'
  done
  for key in "${!SUBST[@]}"; do s=${s//@$key@/${SUBST[$key]}}; done
  left=$(grep -o '@[A-Z_0-9]*@' <<<"$s" | sort -u | tr '\n' ' ' || true)
  [[ -z $left ]] || die "unfilled placeholder(s) in $name: $left"

  explain "Generated script $DEPLOY_DIR/$name: every command line has a comment that says why it is there."
  if [[ $DRY_RUN == 1 ]]; then
    printf '%s\n' "$C_CYAN$(short_paths "$s")$C_RESET" | sed 's/^/  | /'
  else
    mkdir -p "$DEPLOY_DIR"
    printf '%s\n' "$s" >"$DEPLOY_DIR/$name"
    info "Wrote $DEPLOY_DIR/$name ($(grep -vc '^#\|^$' "$DEPLOY_DIR/$name") commands)"
  fi
}

# uuu can check a script without a board: syntax, option names and that every file exists.
validate_script() {
  local name=$1
  [[ $DRY_RUN == 1 ]] && { explain "Real run: 'uuu -dry $name' first checks the syntax and that every file named in it exists."; return 0; }
  ( cd "$DEPLOY_DIR" && "$UUU_BIN" -dry "$name" >/dev/null 2>&1 ) ||
    { ( cd "$DEPLOY_DIR" && "$UUU_BIN" -dry "$name" 2>&1 | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' | tail -3 ) >&2
      die "uuu does not accept $DEPLOY_DIR/$name (see above): is a file missing? run ./build.sh all"; }
  info "uuu -dry: $name parses, all files exist"
}

# Wait until the board is where the script starts, or explain why not.
check_board() {
  if [[ $DRY_RUN == 1 ]]; then
    explain "Real run: checks that the PC sees the board in serial download mode (1fc9:0146), or U-Boot in fastboot (1fc9:0152)."
    return 0
  fi
  local st
  if ! command -v lsusb >/dev/null 2>&1; then
    warn "lsusb not found (sudo apt install usbutils): cannot pre-check the board; uuu waits ${UUU_WAIT_FIRST} s for it"
    return 0
  fi
  st=$(usb_state)
  case $st in
    rom)
      ((NO_SPL == 0)) || die "--no-spl, but the board is in serial download mode (1fc9:0146), not running U-Boot yet: leave out --no-spl"
      info "Board found in serial download mode (USB 1fc9:0146)" ;;
    fastboot)
      if ((NO_SPL == 0)); then
        info "U-Boot is already running in fastboot mode (USB 1fc9:0152): skipping the ROM phase (--no-spl)"
        NO_SPL=1
      else
        info "Board found in U-Boot fastboot mode (USB 1fc9:0152)"
      fi ;;
    *)
      if ((NO_SPL == 1)); then
        board_checklist; die "--no-spl needs U-Boot running in fastboot (USB 1fc9:0152); run './build.sh uuu spl' first"
      fi
      board_checklist; die "no board in serial download mode" ;;
  esac
}

# -----------------------------------------------------------------------------
# uuu deps
# -----------------------------------------------------------------------------
do_deps() {
  section "uuu $UUU_VERSION (NXP Universal Update Utility)"
  explain "uuu is a single executable from github.com/nxp-imx/mfgtools. The pinned release is downloaded into" \
          "build/tools/ and checked against a sha256 stored in config/imx8mp-var-dart.conf."
  [[ $(uname -s) == Linux ]] || die "this script supports Linux hosts; on other systems install uuu $UUU_VERSION from https://github.com/nxp-imx/mfgtools/releases and set UUU_BIN=/path/to/uuu"
  local asset sha
  case $(uname -m) in
    x86_64)        asset=uuu;         sha=$UUU_X86_64_SHA256 ;;
    aarch64|arm64) asset=uuu_aarch64; sha=$UUU_AARCH64_SHA256 ;;
    *) cat >&2 <<EOF
No pinned binary for $(uname -m). Build it from the pinned source instead:
  sudo apt-get install libusb-1.0-0-dev libbz2-dev libzstd-dev libtinyxml2-dev pkg-config cmake libssl-dev g++ zlib1g-dev
  wget $UUU_BASE_URL/uuu_source-uuu_${UUU_VERSION}.tar.gz   # sha256 $UUU_SOURCE_SHA256
  tar xf uuu_source-uuu_${UUU_VERSION}.tar.gz && cd uuu_source-uuu_${UUU_VERSION} && cmake . && make
then:  UUU_BIN=\$PWD/uuu/uuu ./build.sh uuu check
EOF
       die "unsupported CPU architecture $(uname -m)" ;;
  esac
  if [[ -x $UUU_BIN ]]; then
    info "Already installed: $UUU_BIN"
  else
    fetch "$UUU_BASE_URL/$asset" "$DL_DIR/$asset-$UUU_VERSION" "$sha"
    run "Create the tools directory" mkdir -p "$UUU_TOOLS"
    run "Install it as uuu-$UUU_VERSION" cp "$DL_DIR/$asset-$UUU_VERSION" "$UUU_BIN"
    run "Make it executable" chmod +x "$UUU_BIN"
  fi
  if [[ $DRY_RUN != 1 ]]; then
    local missing
    missing=$(ldd "$UUU_BIN" 2>/dev/null | awk '/not found/ {print $1}' | tr '\n' ' ')
    [[ -z $missing ]] || die "uuu needs libraries that are not installed: $missing -> sudo apt install libusb-1.0-0 libzstd1 libbz2-1.0 zlib1g"
    info "$("$UUU_BIN" -h 2>&1 | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' | head -n1 || true)"
  fi
  explain "USB access without sudo: run './build.sh uuu udev' once. lsusb comes from the 'usbutils' package."
  command -v lsusb >/dev/null 2>&1 || warn "lsusb not found: sudo apt install usbutils (./build.sh deps --install)"
}

# -----------------------------------------------------------------------------
# uuu udev
# -----------------------------------------------------------------------------
do_udev() {
  resolve_uuu
  section "udev rule for uuu"
  explain "Linux gives USB devices to root by default. uuu prints a ready-made rule that tags the NXP boot" \
          "devices (ROM 1fc9:0146, fastboot 1fc9:0152 ...) 'uaccess': the user logged in at the machine may use them."
  if [[ $DRY_RUN != 1 ]]; then
    echo "  It will write /etc/udev/rules.d/70-uuu.rules with sudo."
    confirm "Install the rule?" || die "aborted"
  fi
  run_sh "Write the rules uuu prints (only its SUBSYSTEM lines) to /etc/udev/rules.d" \
    "'$UUU_BIN' -udev | sed -n '/^SUBSYSTEM/p' | sudo tee /etc/udev/rules.d/70-uuu.rules >/dev/null"
  run "Load the new rule" sudo udevadm control --reload
  run "Apply it to devices that are already plugged in" sudo udevadm trigger
  explain "Unplug and re-plug the board's USB cable. Over ssh (no local seat) 'uaccess' does not apply: use --sudo."
}

# -----------------------------------------------------------------------------
# uuu check
# -----------------------------------------------------------------------------
do_check() {
  section "What the PC sees on USB"
  explain "ROM serial download = 1fc9:0146; U-Boot fastboot gadget = 1fc9:0152 (CONFIG_USB_GADGET_PRODUCT_NUM of Variscite's U-Boot)."
  if [[ $DRY_RUN == 1 ]]; then
    run_sh "List NXP devices (vendor 1fc9)" "lsusb | grep -i 1fc9 || true"
    return 0
  fi
  command -v lsusb >/dev/null 2>&1 && { lsusb | grep -i '1fc9' | sed 's/^/  /' || true; }
  if [[ -x $UUU_BIN ]]; then
    "$UUU_BIN" -lsusb 2>&1 | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' | grep -v '^$' | tail -n +2 | sed 's/^/  uuu: /' || true
  fi
  case $(usb_state) in
    rom)      info "Board in serial download mode: ready for 'uuu spl', 'uuu boot' or 'uuu emmc'" ;;
    fastboot) info "U-Boot is running in fastboot mode: continue with 'uuu emmc --no-spl' (or power-cycle to start over)" ;;
    *)        board_checklist ;;
  esac
}

# -----------------------------------------------------------------------------
# uuu spl
# -----------------------------------------------------------------------------
do_spl() {
  resolve_uuu
  section "U-Boot over USB (nothing is written)"
  explain "The ROM loads the SPL from the host, the SPL trains the DDR and loads TF-A and U-Boot from the host as well." \
          "U-Boot sees it was started from USB and turns the port into a fastboot gadget. The board then waits."
  need_file "$BOOT_BIN"
  check_board
  if ((NO_SPL == 1)); then info "U-Boot is already running: nothing to do"; return 0; fi
  SUBST[FLASH_BIN]=imx-boot.bin
  gen_script uuu-spl.uuu spl 10-spl
  validate_script uuu-spl.uuu
  run_uuu uuu-spl.uuu "Send imx-boot.bin to the Boot ROM; U-Boot comes up in fastboot mode"
  explain "Next: ./build.sh uuu emmc --no-spl   or   power-cycle to start over."
}

# -----------------------------------------------------------------------------
# uuu emmc
# -----------------------------------------------------------------------------
do_emmc() {
  resolve_uuu
  section "Flash the on-module eMMC over USB ($EMMC_MODE)"
  explain "The ROM, SPL and U-Boot run from RAM (phase 1). U-Boot's fastboot then writes the eMMC (phase 3)." \
          "The eMMC is the module's, device ${EMMC_DEV} in U-Boot; the SD slot (device 1) is never touched."

  local image bmap="" blks=0 size=0 cmdname=emmc
  image=$(readlink -f "$DEPLOY_DIR/sdcard.img" 2>/dev/null || true)
  [[ -n $image && -e $image ]] || image="$DEPLOY_DIR/sdcard.img"
  [[ $EMMC_MODE == bootloader ]] || need_file "$image"
  [[ $EMMC_MODE == rootfs ]] || need_file "$BOOT_BIN"
  if [[ $DRY_RUN != 1 ]]; then
    [[ $EMMC_MODE == rootfs ]] || { size=$(stat -c %s "$BOOT_BIN"); blks=$(( (size + 511) / 512 )); }
    [[ -f $image.bmap ]] && bmap=$(basename "$image").bmap
    [[ $EMMC_MODE == bootloader || -n $bmap ]] || warn "no $(basename "$image").bmap (needs bmap-tools): the whole image is sent, slower"
  fi
  [[ $EMMC_MODE == full ]] || cmdname+=" --$EMMC_MODE-only"

  # Where is the board? (decides whether the ROM phase is part of the script)
  check_board
  ((NO_SPL == 0)) || cmdname+=" --no-spl"

  SUBST[FLASH_BIN]=imx-boot.bin
  SUBST[IMAGE]=$(basename "$image")
  if [[ -n $bmap ]]; then SUBST[BMAP_ARGS]="-bmap $bmap"
  elif [[ $DRY_RUN == 1 ]]; then SUBST[BMAP_ARGS]="-bmap <image>.bmap"
  else SUBST[BMAP_ARGS]=""; fi
  SUBST[P1_OFFSET]=$(hex $(( ROOTFS_PART_START_MB * 1024 * 1024 )))
  SUBST[ENV_SIZE]=$EMMC_ENV_SIZE
  SUBST[ENV_BLK]=$(hex $(( EMMC_ENV_OFFSET / 512 )))
  SUBST[ENV_BLKS]=$(hex $(( (EMMC_ENV_SIZE + 511) / 512 )))
  SUBST[BOOT_OFFSET_BLK]=$(hex $(( EMMC_BOOT_OFFSET_KB * 2 )))
  if [[ $DRY_RUN == 1 ]]; then SUBST[BOOT_BLKS]="<size of imx-boot.bin in 512-byte blocks>"
  else SUBST[BOOT_BLKS]=$(hex "$blks"); fi
  SUBST[BOOT_PART]=$EMMC_BOOT_PART
  SUBST[BOOT_ACK]=$EMMC_BOOT_ACK
  SUBST[FB_BUF]=$UUU_FASTBOOT_BUF

  local frags=()
  ((NO_SPL == 1)) || frags+=(10-spl)
  frags+=(20-emmc-select)
  case $EMMC_MODE in
    full)       frags+=(30-emmc-user-full 40-emmc-boot) ;;
    rootfs)     frags+=(30-emmc-user-rootfs) ;;
    bootloader) frags+=(40-emmc-boot) ;;
  esac
  frags+=(90-finish)

  gen_script uuu-emmc.uuu "$cmdname" "${frags[@]}"
  validate_script uuu-emmc.uuu

  if [[ $DRY_RUN != 1 ]]; then
    echo
    echo "  ${C_BOLD}About to write the eMMC of the board on the USB cable${C_RESET} (mode: $EMMC_MODE):"
    case $EMMC_MODE in
      full)       echo "    - the WHOLE user area: partition table, root filesystem, saved U-Boot environment (what is there is lost)"
                  echo "    - imx-boot.bin into boot0 and boot1, and the ROM boot configuration (boot0, ack $EMMC_BOOT_ACK)" ;;
      rootfs)     echo "    - the root filesystem (partition 1, from $ROOTFS_PART_START_MB MiB on); the rest of the eMMC is kept" ;;
      bootloader) echo "    - imx-boot.bin into boot0 and boot1, and the ROM boot configuration (boot0, ack $EMMC_BOOT_ACK)" ;;
    esac
    echo "    The SD card slot is not touched. Recovery from a bad result is always possible over USB."
    echo
    confirm "Write the eMMC now?" || die "aborted by user"
  fi

  run_uuu uuu-emmc.uuu "Run phase 1 (ROM, SPL, U-Boot) and the eMMC writes of the script above"

  if [[ $DRY_RUN != 1 ]]; then
    section "eMMC written"
    cat <<EOF
  Now boot from it:
    1. power the board off and unplug the USB cable (or keep it: the ROM does not use it in eMMC boot);
    2. set the boot switch to eMMC (your carrier's manual; Variscite's SMARC/Sonata kit guide: SW7 = 1 ON, 2-4 OFF);
    3. power on and watch the serial console: the SPL should print
         Boot Stage: Primary boot
         image offset 0x0, pagesize 0x200, ivt offset 0x0       <- 0x0 = boot partition (SD says 0x8000)
    4. U-Boot then prints  MMC: ... and mounts root=/dev/mmcblk2p1. See docs/16-booting-from-emmc-with-uuu.md.
  Back to SD boot: boot switch to SD with the card in. Nothing on the eMMC needs to be undone.
EOF
  fi
}

# -----------------------------------------------------------------------------
# uuu boot (RAM boot)
# -----------------------------------------------------------------------------
prepare_ram_boot() {
  local ktar="$DEPLOY_DIR/kernel.tar.gz" rtar="$DEPLOY_DIR/rootfs.tar" ovl="$DEPLOY_DIR/kernel/boot"
  need_file "$ktar" "$rtar" "$ovl/Image.gz"

  if [[ -z $DTB ]]; then
    if [[ $DRY_RUN == 1 ]]; then
      DTB='<your-dtb>.dtb'
      explain "Real run: --dtb NAME is required (U-Boot's automatic DTB choice is lost when it is started from USB)."
    else
      echo "  Device trees available in $ovl:" >&2
      (cd "$ovl" && ls ./*.dtb 2>/dev/null | sed 's|^\./|    |' | grep 'imx8mp-var-\(som\|dart\|smarc\)' | head -n 60) >&2 || true
      die "which device tree? use --dtb NAME (e.g. imx8mp-var-som-symphony.dtb, imx8mp-var-dart-sonata.dtb); the name pattern is explained in docs/04-kernel.md"
    fi
  fi
  [[ $DRY_RUN == 1 || -f $ovl/$DTB ]] || die "device tree $DTB not found in $ovl (./build.sh kernel builds them)"
  if [[ -z $CONSOLE ]]; then
    case $DTB in
      imx8mp-var-dart*) CONSOLE=ttymxc0 ;;
      *)                CONSOLE=ttymxc1 ;;
    esac
    explain "Serial console guessed from the DTB name: $CONSOLE (DART: ttymxc0, VAR-SOM / SMARC: ttymxc1). Override with --console."
  fi

  run "Create the directory for the RAM-boot files" mkdir -p "$RAM_DIR"
  run_sh "Decompress the kernel: booti starts an uncompressed Image, and it is loaded straight to \${loadaddr}" \
    "gzip -dc '$ovl/Image.gz' > '$RAM_DIR/Image'"

  local mkimage="$SRC_DIR/uboot-imx/tools/mkimage"
  [[ -x $mkimage || $DRY_RUN == 1 ]] || { mkimage=$(command -v mkimage || true); [[ -n $mkimage ]] || die "mkimage not found: build U-Boot first (./build.sh uboot) or install u-boot-tools"; }

  explain "Initramfs: the root filesystem + the kernel overlay (modules) as one gzip-compressed cpio archive, which Linux" \
          "unpacks into RAM and runs /sbin/init from. fakeroot keeps the files owned by root, as in the SD image."
  run "Build the initramfs (as fake root)" \
    fakeroot -- bash -euc '
      stage=$1 rootfs=$2 kernel=$3 out=$4
      rm -rf "$stage"; mkdir -p "$stage"
      tar -xpf "$rootfs" -C "$stage" --numeric-owner
      tar -xpf "$kernel" -C "$stage" --numeric-owner --keep-directory-symlink
      (cd "$stage" && find . | cpio --quiet -o -H newc | gzip -6 > "$out")
      rm -rf "$stage"
    ' _ "$WORK_DIR/ram-rootfs" "$rtar" "$ktar" "$RAM_DIR/rootfs.cpio.gz"
  run "Wrap it in a U-Boot ramdisk header so 'booti' knows its size (no further compression)" \
    "$mkimage" -A arm64 -O linux -T ramdisk -C none -n var-ram-rootfs -d "$RAM_DIR/rootfs.cpio.gz" "$RAM_DIR/initramfs.cpio.gz.uboot"
  run "Remove the unwrapped copy" rm -f "$RAM_DIR/rootfs.cpio.gz"

  if [[ $DRY_RUN != 1 ]]; then
    local sz; sz=$(stat -c %s "$RAM_DIR/initramfs.cpio.gz.uboot")
    info "initramfs: $(hsize "$RAM_DIR/initramfs.cpio.gz.uboot") compressed, kernel Image: $(hsize "$RAM_DIR/Image")"
    (( sz < 1024 * 1024 * 1024 )) || die "the initramfs is larger than U-Boot's 1 GiB fastboot buffer: use a smaller root filesystem (./build.sh -r alpine)"
    (( sz < 400 * 1024 * 1024 )) || warn "a big initramfs ($((sz / 1048576)) MiB) needs about 3x that in RAM once unpacked; the Alpine root filesystem is the safe choice for RAM boot"
  fi
}

do_boot() {
  resolve_uuu
  section "Run Linux from RAM over USB (nothing is written)"
  explain "Same first phase as 'uuu spl'. Then kernel, device tree and the root filesystem (as an initramfs) are sent into RAM" \
          "and U-Boot's 'booti' starts them. Power-cycle and the board is as it was: no storage is read or written."
  prepare_ram_boot
  SUBST[FLASH_BIN]=imx-boot.bin
  need_file "$BOOT_BIN"
  SUBST[KERNEL]=uuu-ram/Image
  SUBST[DTB]=kernel/boot/$DTB
  SUBST[INITRAMFS]=uuu-ram/initramfs.cpio.gz.uboot
  SUBST[CONSOLE]=$CONSOLE
  check_board
  local frags=() cmdname=boot
  ((NO_SPL == 1)) && cmdname+=" --no-spl" || frags+=(10-spl)
  frags+=(50-ram-boot)
  gen_script uuu-boot.uuu "$cmdname" "${frags[@]}"
  validate_script uuu-boot.uuu
  run_uuu uuu-boot.uuu "Load U-Boot, then kernel + device tree + initramfs into RAM and start Linux"
  [[ $DRY_RUN == 1 ]] || info "Linux was started. Watch the serial console ($CONSOLE, 115200 8N1). Power-cycle to return to the normal state."
}

# -----------------------------------------------------------------------------
main() {
  local sub=${1:-help}
  (($#)) && shift
  while (($#)); do
    case $1 in
      --rootfs-only)       EMMC_MODE=rootfs ;;
      --bootloader-only)   EMMC_MODE=bootloader ;;
      --no-spl)            NO_SPL=1 ;;
      --sudo)              USE_SUDO=1 ;;
      --dtb)               DTB=$2; shift ;;
      --console)           CONSOLE=$2; shift ;;
      -y|--yes)            ASSUME_YES=1 ;;
      -n|--dry-run)        DRY_RUN=1 ;;
      -h|--help)           usage 0 ;;
      *) warn "unknown option $1"; usage 1 ;;
    esac
    shift
  done

  case $sub in
    help|-h|--help) usage 0 ;;
    deps)  start_log "uuu-deps";  do_deps ;;
    udev)  start_log "uuu-udev";  do_udev ;;
    check) do_check ;;
    spl)   start_log "uuu-spl";   do_spl ;;
    boot)  start_log "uuu-boot";  do_boot ;;
    emmc)  start_log "uuu-emmc";  do_emmc ;;
    *) warn "unknown uuu command '$sub'"; usage 1 ;;
  esac
}

main "$@"
