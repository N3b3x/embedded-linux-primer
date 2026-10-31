#!/usr/bin/env bash
# =============================================================================
#  scripts/firmware.sh - build the STM32MP15 boot chain: BL2, OP-TEE, U-Boot, FIP
# =============================================================================
#
#  The STM32MP15 Boot ROM can only load ONE small program, BL2, from the SD card
#  (from the partition named "fsbl1"). BL2 then trains the DRAM and loads a
#  second container, the FIP ("Firmware Image Package"), from the partition of
#  type "fip". The FIP holds everything else that boots the board:
#
#    1. OP-TEE OS (3 files)     the trusted OS AND the secure monitor (PL1 secure);
#                               also the SCMI server for clocks, resets, regulators
#    2. U-Boot + its DTB        the normal-world bootloader (BL33)
#    3. fw-config DTB           tells BL2 where/how to load the above
#
#  There is no BL31 (that is the 64-bit world) and no DDR firmware blob: the DDR3
#  controller driver is part of BL2 itself.
#
#  This script, step by step (each is a standalone sub-command):
#
#    optee   build tee-header_v2.bin / tee-pager_v2.bin / tee-pageable_v2.bin from OP-TEE
#    uboot   build u-boot-nodtb.bin / u-boot.dtb
#    tfa     build BL2 (tf-a-stm32mp157f-dk2.stm32)
#    fip     pack everything into fip.bin with TF-A's fiptool
#
#  Usage: scripts/firmware.sh [all|optee|uboot|tfa|fip|menuconfig|clean]
#         (normally called through ./build.sh firmware)
# =============================================================================
# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
strict_mode
load_config

TFA_SRC="$SRC_DIR/trusted-firmware-a"
OPTEE_SRC="$SRC_DIR/optee_os"
UBOOT_SRC="$SRC_DIR/u-boot"

# Out-of-tree build directories: the source checkouts stay pristine.
TFA_OUT="$WORK_DIR/tf-a"
OPTEE_OUT="$WORK_DIR/optee"
UBOOT_OUT="$WORK_DIR/u-boot"
TFA_BUILD="$TFA_OUT/$TFA_PLATFORM/release"

# The BL2 image TF-A makes is named after the device tree:
# stm32mp157f-dk2.dtb -> tf-a-stm32mp157f-dk2.stm32
BL2_NAME="tf-a-${TFA_DTB%.dtb}.stm32"

# -----------------------------------------------------------------------------
do_optee() {
  use_toolchain elf
  section "OP-TEE OS $OPTEE_BRANCH for $OPTEE_PLATFORM ($OPTEE_DTS)"
  explain "OP-TEE is the trusted OS. On this 32-bit SoC it is also the secure monitor" \
          "(there is no BL31) and the SCMI server: Linux asks it to enable clocks," \
          "release resets and switch the regulators that only the secure world may touch."
  git_checkout "optee_os" "$OPTEE_REPO" "$OPTEE_BRANCH" "$OPTEE_REV" "$OPTEE_SRC"
  apply_patches optee "$OPTEE_SRC"
  # ARCH=arm is OP-TEE's name for both 32 and 64 bit ARM; the platform decides
  # (plat-stm32mp1 builds a 32-bit core). CFG_EMBED_DTB_SOURCE_FILE picks the
  # board's device tree, compiled into the OP-TEE image: it tells the secure OS
  # which peripherals it owns (ETZPC setup, SCMI clocks, UART4...). The same file
  # also selects the 512 MB memory flavour (secure RAM at 0xde000000).
  # The pager is on by default for STM32MP15, hence three output files.
  run "Build the OP-TEE core (plain make, not run_make: it is not a Linux-style build)" \
    make -C "$OPTEE_SRC" -j"$JOBS" O="$OPTEE_OUT" \
      CROSS_COMPILE32="$CROSS_COMPILE" ARCH=arm PLATFORM="$OPTEE_PLATFORM" \
      CFG_EMBED_DTB_SOURCE_FILE="$OPTEE_DTS" \
      CFG_TEE_CORE_LOG_LEVEL=2 all
  if [[ $DRY_RUN != 1 ]]; then
    local f
    mkdir -p "$DEPLOY_DIR"
    for f in tee-header_v2.bin tee-pager_v2.bin tee-pageable_v2.bin; do
      cp "$OPTEE_OUT/core/$f" "$DEPLOY_DIR/$f"
    done
    info "OP-TEE: $(hsize "$DEPLOY_DIR/tee-pager_v2.bin") pager + $(hsize "$DEPLOY_DIR/tee-pageable_v2.bin") pageable in $DEPLOY_DIR"
  fi
}

# -----------------------------------------------------------------------------
do_uboot_cfg() {
  use_toolchain linux
  section "U-Boot $UBOOT_BRANCH ($UBOOT_DEFCONFIG)"
  git_checkout "u-boot" "$UBOOT_REPO" "$UBOOT_BRANCH" "$UBOOT_REV" "$UBOOT_SRC"
  apply_patches u-boot "$UBOOT_SRC"
  if [[ -f $UBOOT_OUT/.config && ${FORCE_CONFIG:-0} != 1 ]]; then
    info "Keeping existing U-Boot .config (FORCE_CONFIG=1 to regenerate)"
  else
    run "Create the output directory" mkdir -p "$UBOOT_OUT"
    run_make "Create U-Boot's .config from configs/$UBOOT_DEFCONFIG" "$UBOOT_SRC" O="$UBOOT_OUT" "$UBOOT_DEFCONFIG"
  fi
}

do_uboot() {
  do_uboot_cfg
  explain "U-Boot here is BL33: BL2 loads it into DRAM and OP-TEE starts it in the normal world." \
          "TF-A wants two files from it: u-boot-nodtb.bin (the program) and u-boot.dtb" \
          "(its own device tree, passed as BL33_CFG)."
  run_make "Compile U-Boot for the $UBOOT_DEVICE_TREE device tree" "$UBOOT_SRC" O="$UBOOT_OUT" \
    DEVICE_TREE="$UBOOT_DEVICE_TREE" all
  if [[ $DRY_RUN != 1 ]]; then
    mkdir -p "$DEPLOY_DIR"
    cp "$UBOOT_OUT/u-boot-nodtb.bin" "$UBOOT_OUT/u-boot.dtb" "$DEPLOY_DIR/"
    info "U-Boot: $(hsize "$DEPLOY_DIR/u-boot-nodtb.bin") + $(hsize "$DEPLOY_DIR/u-boot.dtb") DTB"
  fi
}

# -----------------------------------------------------------------------------
# Arguments shared by the `tfa` and `fip` builds. Both must use identical flags,
# otherwise make rebuilds BL2 with different settings.
tfa_args() {
  TFA_ARGS=(
    PLAT="$TFA_PLATFORM" ARCH=aarch32 ARM_ARCH_MAJOR=7 CROSS_COMPILE="$CROSS_COMPILE"
    DTB_FILE_NAME="$TFA_DTB" "$TFA_BOOT_FLAG"
    "$TFA_SPD" LOG_LEVEL="$TFA_LOG_LEVEL"
    BUILD_BASE="$TFA_OUT"
  )
}

do_tfa() {
  use_toolchain elf
  need_cmd dtc
  section "TF-A $TFA_BRANCH for $TFA_PLATFORM / $TFA_DTB (BL2 only)"
  git_checkout "trusted-firmware-a" "$TFA_REPO" "$TFA_BRANCH" "$TFA_REV" "$TFA_SRC"
  apply_patches tf-a "$TFA_SRC"
  tfa_args
  explain "BL2 is linked to run from the SoC's internal SRAM (SYSRAM) and gets an" \
          "STM32 image header (the Boot ROM checks it) -> $BL2_NAME." \
          "AARCH32_SP=optee tells it that the next stage is OP-TEE, not TF-A's SP_min."
  run "Build BL2 (+STM32 header) and the device trees" \
    make -C "$TFA_SRC" -j"$JOBS" "${TFA_ARGS[@]}" all
  if [[ $DRY_RUN != 1 ]]; then
    mkdir -p "$DEPLOY_DIR"
    cp "$TFA_BUILD/$BL2_NAME" "$DEPLOY_DIR/$BL2_NAME"
    info "BL2: $(hsize "$DEPLOY_DIR/$BL2_NAME") -> $DEPLOY_DIR/$BL2_NAME"
  fi
}

do_fip() {
  use_toolchain elf
  need_cmd dtc
  section "FIP: pack OP-TEE + U-Boot + the device trees"
  tfa_args
  need_file "$DEPLOY_DIR/tee-header_v2.bin" "$DEPLOY_DIR/tee-pager_v2.bin" \
            "$DEPLOY_DIR/tee-pageable_v2.bin" \
            "$DEPLOY_DIR/u-boot-nodtb.bin" "$DEPLOY_DIR/u-boot.dtb"
  explain "fiptool (built from TF-A's tools/fiptool) writes a table of contents with a" \
          "UUID per image, then the images back to back. BL2 looks the images up by UUID:" \
          "  BL32 = OP-TEE header (28 bytes), BL32_EXTRA1 = the OP-TEE pager image (--tos-fw-extra1)," \
          "  BL32_EXTRA2 = the pageable part (--tos-fw-extra2; the pager is on for STM32MP15)," \
          "  BL33 = U-Boot, BL33_CFG = U-Boot's DTB (--hw-config)."
  run "Build the FIP" \
    make -C "$TFA_SRC" -j"$JOBS" "${TFA_ARGS[@]}" \
      BL33="$DEPLOY_DIR/u-boot-nodtb.bin" BL33_CFG="$DEPLOY_DIR/u-boot.dtb" \
      BL32="$DEPLOY_DIR/tee-header_v2.bin" \
      BL32_EXTRA1="$DEPLOY_DIR/tee-pager_v2.bin" \
      BL32_EXTRA2="$DEPLOY_DIR/tee-pageable_v2.bin" \
      fip
  if [[ $DRY_RUN != 1 ]]; then
    cp "$TFA_BUILD/fip.bin" "$DEPLOY_DIR/fip.bin"
    cp "$TFA_BUILD/$BL2_NAME" "$DEPLOY_DIR/$BL2_NAME"
    run "List what is inside the FIP" "$TFA_SRC/tools/fiptool/fiptool" info "$DEPLOY_DIR/fip.bin"
    local fip_max=$(( FIP_SIZE_KB * 1024 ))
    (( $(stat -c %s "$DEPLOY_DIR/fip.bin") <= fip_max )) ||
      die "fip.bin is larger than the ${FIP_SIZE_KB} KiB 'fip' partition; raise FIP_SIZE_KB"
    info "FIP: $(hsize "$DEPLOY_DIR/fip.bin") of ${FIP_SIZE_KB} KiB partition"
  fi
}

do_menuconfig() {
  do_uboot_cfg
  run_make "Open U-Boot's interactive configuration menu" "$UBOOT_SRC" O="$UBOOT_OUT" menuconfig
  info "Your changes are in $UBOOT_OUT/.config. To keep them, save a fragment in patches/ (see docs/08)."
}

do_clean() {
  section "Cleaning firmware build outputs (sources and downloads are kept)"
  run "Remove the out-of-tree build directories" rm -rf "$TFA_OUT" "$OPTEE_OUT" "$UBOOT_OUT"
  run "Remove the deployed firmware files" rm -f "$DEPLOY_DIR"/tf-a-*.stm32 "$DEPLOY_DIR"/fip.bin \
    "$DEPLOY_DIR"/tee-*_v2.bin "$DEPLOY_DIR"/u-boot-nodtb.bin "$DEPLOY_DIR"/u-boot.dtb
}

main() {
  local target=${1:-all}
  [[ $target == menuconfig ]] || start_log "firmware-$target"
  case $target in
    all)        do_optee; do_uboot; do_tfa; do_fip ;;
    optee)      do_optee ;;
    uboot)      do_uboot ;;
    tfa)        do_tfa ;;
    fip)        do_fip ;;
    menuconfig) do_menuconfig ;;
    clean)      do_clean ;;
    *) die "unknown target '$target' (all|optee|uboot|tfa|fip|menuconfig|clean)" ;;
  esac
}

main "$@"
