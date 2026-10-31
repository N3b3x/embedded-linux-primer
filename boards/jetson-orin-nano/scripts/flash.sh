#!/usr/bin/env bash
# =============================================================================
#  scripts/flash.sh - flash the board over USB (Force Recovery Mode)
# =============================================================================
#
#  Not an SD-card writer: there is no card to write on the PC. NVIDIA's tool
#  boots a small Linux (the "initrd") on the Jetson over the USB-C cable, then
#  the PC exports the images over NFS, through an Ethernet-over-USB link, and
#  that Linux writes them to the QSPI-NOR chip and to the SD/NVMe/USB device.
#  docs/11-recovery-and-usb-flash.md walks through every step.
#
#  Safety checks before anything is written:
#    - a Jetson must be in Force Recovery Mode (lsusb shows 0955:xxxx)
#    - the plan is printed: board, root device, what gets erased
#    - you confirm
#
#  Modes:
#    (default)   use the package from ./build.sh image if there is one,
#                otherwise generate it and flash in one go
#    --full      regenerate the package and flash in one go
#    --check     only look for a board in recovery mode, change nothing
#
#  Options:  -y/--yes   do not ask      -n/--dry-run   print the commands only
#
#  Usage: scripts/flash.sh [--full] [--check]
# =============================================================================
# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
strict_mode
load_config

MODE=auto

while (($#)); do
  case $1 in
    --full)       MODE=full ;;
    --check)      MODE=check ;;
    -y|--yes)     ASSUME_YES=1 ;;
    -n|--dry-run) DRY_RUN=1 ;;
    -h|--help)    sed -n '/^#  Modes:/,/^# ====/p' "$0" | sed 's/^# \{0,1\}//; /^====/d'; exit 0 ;;
    *) die "unknown option $1" ;;
  esac
  shift
done

how_to_recover() {
  cat <<EOM

  The Orin Nano Developer Kit is not in Force Recovery Mode. NVIDIA's Quick Start:
    1. Disconnect the power cable (the kit must be OFF).
    2. Put a jumper on the 12-pin button header, shorting the pins labelled
       FC REC (Force Recovery) and GND.
    3. Connect the USB-C port of the kit to this PC (preferably directly, no hub).
    4. Reconnect the power cable.
    5. Check:  lsusb -d 0955:   -> expect  ID 0955:7523 NVidia Corp.  (Orin Nano 8GB)
       (0955:7623 = Orin Nano 4GB; 0955:7323 / 0955:7423 = Orin NX on this carrier)
  Remove the jumper after flashing: while it is fitted, every power-up enters recovery mode.
EOM
}

main() {
  start_log "flash"
  host_check
  need_cmd lsusb sudo
  section "Looking for a Jetson in Force Recovery Mode"
  local found
  found=$(recovery_devices)
  if [[ -z $found ]]; then
    if [[ $DRY_RUN == 1 ]]; then
      warn "no Jetson in recovery mode found (ignored in dry-run)"
    else
      how_to_recover
      die "no Jetson in Force Recovery Mode on the USB bus"
    fi
  else
    printf '%s\n' "$found" | sed 's/^/  /'
    [[ $(printf '%s\n' "$found" | wc -l) -le 1 ]] || die "more than one Jetson in recovery mode; NVIDIA's tool needs exactly one"
  fi
  [[ $MODE == check ]] && { info "A board is in recovery mode and ready to flash."; return 0; }

  initrd_flash_args
  local use_package=0
  if [[ $MODE == auto && -f $WORK_DIR/.stamp-image ]]; then use_package=1; fi

  echo
  echo "  Board configuration : $BOARD"
  echo "  Root device         : $ROOT_DEVICE  (/dev/$(external_device) on the board)"
  echo "  Will overwrite      : the 64 MiB QSPI-NOR boot flash on the module"
  echo "                        AND the whole $ROOT_DEVICE device attached to the board"
  echo "  Package             : $([[ $use_package == 1 ]] && echo 'from ./build.sh image' || echo 'generated now, then flashed')"
  echo
  [[ $DRY_RUN == 1 ]] || confirm "Flash the Jetson now?" || die "aborted by user"

  run_cd "NVIDIA's flash scripts run from the top of Linux_for_Tegra" "$L4T_DIR"
  explain "The tool installs temporary udev rules and an NFS export on this PC, boots" \
          "a recovery initrd on the Jetson, and cleans up again when it exits."
  if [[ $use_package == 1 ]]; then
    run "Flash the package generated earlier" \
      sudo ./tools/kernel_flash/l4t_initrd_flash.sh --flash-only --network "$FLASH_NETWORK"
  else
    run "Generate the package and flash it" \
      sudo env "${INITRD_ENV[@]}" ./tools/kernel_flash/l4t_initrd_flash.sh "${INITRD_ARGS[@]}" "$BOARD" internal
  fi

  [[ $DRY_RUN == 1 ]] || cat <<EOM

  Flashing finished. The kit reboots by itself.
    - Remove the FC REC jumper now, if you have not already.
    - Serial: with the default user created, there is no setup wizard. Log in as
      '$TARGET_USER' on a monitor (DisplayPort) or over SSH once it has an IP.
      Details and the serial options: docs/07-flashing-and-booting.md
EOM
}

main "$@"
