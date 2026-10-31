#!/usr/bin/env bash
# =============================================================================
#  scripts/image.sh - generate the flash package (the Jetson's "SD card image")
# =============================================================================
#
#  The SD-card boards of this repository end with one file, sdcard.img. A
#  Jetson has no such file: NVIDIA's tool turns the Linux_for_Tegra tree into a
#  FLASH PACKAGE, a set of signed partition images plus an initrd that will do
#  the writing on the board:
#
#      Linux_for_Tegra/bootloader/            QSPI-NOR images (MB1, MB2, UEFI, ...)
#      Linux_for_Tegra/tools/kernel_flash/images/   external device images
#                                             (kernel, kernel-dtb, esp, APP = rootfs)
#
#  This script runs l4t_initrd_flash.sh with --no-flash, which does exactly
#  that and stops. The board is flashed later by ./build.sh flash, so the slow
#  part (building a multi-GB rootfs image) is separate from the part that needs
#  the board and a cable.
#
#  Online or offline: with a board in Force Recovery Mode on the USB port, the
#  tool reads the module's identity (SKU, FAB) from it. Without a board it
#  needs those values on the command line; config/jetson-orin-nano.conf holds
#  the table values for the Orin Nano 8GB module. Pass --offline to force that.
#
#  Needs root (loop mounts, ownership). Output summary in build/deploy/.
#
#  Usage: scripts/image.sh [--offline]
# =============================================================================
# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
strict_mode
load_config

OFFLINE=0
while (($#)); do
  case $1 in
    --offline) OFFLINE=1 ;;
    *) die "unknown option $1" ;;
  esac
  shift
done

main() {
  start_log "image"
  host_check
  need_cmd sudo
  section "Flash package for $BOARD, root on $ROOT_DEVICE ($(external_device))"

  if [[ $DRY_RUN != 1 ]]; then
    [[ -f $WORK_DIR/.stamp-default-user ]] || die "the root filesystem is not ready: run ./build.sh rootfs first"
    need_file "$L4T_DIR/tools/kernel_flash/l4t_initrd_flash.sh" "$L4T_DIR/kernel/Image"
  fi

  initrd_flash_args
  local env_words=("${INITRD_ENV[@]}") mode=online
  if [[ $OFFLINE == 1 || -z $(recovery_devices) ]]; then
    mode=offline
    env_words+=("BOARDID=$OFFLINE_BOARDID" "BOARDSKU=$OFFLINE_BOARDSKU" "FAB=$OFFLINE_FAB")
    explain "No board in recovery mode (or --offline): using the module identity from the config" \
            "(BOARDID=$OFFLINE_BOARDID BOARDSKU=$OFFLINE_BOARDSKU FAB=$OFFLINE_FAB). If your module is a different SKU," \
            "put the matching row of README_initrd_flash.txt's table into config/local.conf."
  else
    explain "A board in Force Recovery Mode is connected: the tool will read its identity."
  fi
  info "Mode: $mode"

  # Your own board files (docs/08 section 6) live in the repository, not in build/.
  if compgen -G "$TOP_DIR/custom/boards/*.conf" >/dev/null; then
    run "Copy your board configuration files next to NVIDIA's" cp "$TOP_DIR"/custom/boards/*.conf "$L4T_DIR/"
  fi
  if compgen -G "$TOP_DIR/custom/BCT/*" >/dev/null; then
    run "Copy your boot configuration table files next to NVIDIA's" cp "$TOP_DIR"/custom/BCT/* "$L4T_DIR/bootloader/generic/BCT/"
  fi

  run_cd "NVIDIA's flash scripts run from the top of Linux_for_Tegra" "$L4T_DIR"
  explain "--no-flash : build every image and the flashing initrd, then stop." \
          "-p '-c $QSPI_LAYOUT' : also flash the QSPI-NOR boot firmware, per this XML." \
          "--external-device / -c : the SD/NVMe/USB device and its partition layout." \
          "'$BOARD internal' : board config, and 'root=PARTUUID=...' on the kernel command line."
  run "Generate the flash package (this builds the rootfs image; it takes several minutes)" \
    sudo env "${env_words[@]}" ./tools/kernel_flash/l4t_initrd_flash.sh --no-flash "${INITRD_ARGS[@]}" "$BOARD" internal
  [[ $DRY_RUN == 1 ]] || touch "$WORK_DIR/.stamp-image"

  run "Create the deploy directory" mkdir -p "$DEPLOY_DIR"
  run "Link the working tree, so the artifacts are findable under build/deploy" ln -sfn ../work/Linux_for_Tegra "$DEPLOY_DIR/Linux_for_Tegra"
  if [[ $DRY_RUN != 1 ]]; then
    {
      echo "# Flash package for $BOARD ($ROOT_DEVICE), generated $(date -u +%Y-%m-%dT%H:%MZ), Jetson Linux R$L4T_RELEASE"
      echo "# Put the board in Force Recovery Mode, then:"
      echo "./build.sh flash                      # writes this package"
      echo "# or by hand, from Linux_for_Tegra/:"
      echo "sudo ./tools/kernel_flash/l4t_initrd_flash.sh --flash-only --network $FLASH_NETWORK"
    } >"$DEPLOY_DIR/FLASH.txt"
    section "Done"
    sudo du -sh "$L4T_DIR/tools/kernel_flash/images" "$L4T_DIR/bootloader/signed" 2>/dev/null | sed 's/^/  /' || true
    info "Flash package ready. Put the board in Force Recovery Mode and run:  ./build.sh flash"
  fi
}

main "$@"
