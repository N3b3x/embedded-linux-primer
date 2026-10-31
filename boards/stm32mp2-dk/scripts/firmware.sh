#!/usr/bin/env bash
# =============================================================================
#  scripts/firmware.sh - build the STM32MP257 boot chain: BL2, BL31, OP-TEE, U-Boot, FIP
# =============================================================================
#
#  The STM32MP25 Boot ROM can only load ONE small program, BL2, from the SD card
#  (from the partition named "fsbla1"). BL2 then trains the DRAM and loads a
#  second container, the FIP ("Firmware Image Package"), from the partition of
#  type "fip". The FIP holds everything else that boots the board:
#
#    1. BL31 + its device tree  TF-A's resident secure monitor (EL3)
#    2. OP-TEE OS               the trusted OS (S-EL1); also the SCMI clock/reset server
#    3. U-Boot + its DTB        the normal-world bootloader (BL33)
#    4. DDR PHY firmware        Synopsys training code for the LPDDR4 controller
#    5. fw-config DTB           tells BL2 where/how to load the above
#
#  This script, step by step (each is a standalone sub-command):
#
#    ddr       fetch ST's DDR PHY training firmware
#    optee     build tee-header_v2.bin / tee-pager_v2.bin from OP-TEE
#    uboot     build u-boot-nodtb.bin / u-boot.dtb
#    tfa       build BL2 (tf-a-stm32mp257f-dk.stm32) and BL31
#    fip       pack everything into fip.bin with TF-A's fiptool
#    metadata  STACK=st only: the FWU metadata that tells BL2 to boot fip-a (metadata.bin)
#
#  STACK=st builds ST's own branches instead (config/stack-st.conf). The steps are the
#  same; the places where they differ are marked "STACK=st" below and listed in
#  docs/15-two-stacks.md.
#
#  Usage: scripts/firmware.sh [all|ddr|optee|uboot|tfa|fip|metadata|menuconfig|clean]
#         (normally called through ./build.sh firmware)
# =============================================================================
# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
strict_mode
load_config

TFA_SRC="$SRC_DIR/trusted-firmware-a"
OPTEE_SRC="$SRC_DIR/optee_os"
UBOOT_SRC="$SRC_DIR/u-boot"
DDRFW_SRC="$SRC_DIR/stm32-ddr-phy-binary"
SCPFW_SRC="$SRC_DIR/scp-firmware"

# Out-of-tree build directories: the source checkouts stay pristine.
TFA_OUT="$WORK_DIR/tf-a"
OPTEE_OUT="$WORK_DIR/optee"
UBOOT_OUT="$WORK_DIR/u-boot"
# TF-A puts its output in <BUILD_BASE>/<platform>/release, or .../debug for a DEBUG=1 build.
TFA_BUILD="$TFA_OUT/$TFA_PLATFORM/release"
[[ " $TFA_EXTRA_FLAGS " == *" DEBUG=1 "* ]] && TFA_BUILD="$TFA_OUT/$TFA_PLATFORM/debug"

# The BL2 image TF-A makes is named after the device tree:
# stm32mp257f-dk.dtb -> tf-a-stm32mp257f-dk.stm32
BL2_NAME="tf-a-${TFA_DTB%.dtb}.stm32"

# -----------------------------------------------------------------------------
do_ddr() {
  section "DDR PHY training firmware: $DDRFW_BRANCH"
  explain "The LPDDR4 controller's PHY contains a tiny processor (the PMU) that must run" \
          "ST/Synopsys training code at every power-up to tune the memory timing." \
          "TF-A BL2 loads that code from the FIP; it is a binary blob, not source."
  git_checkout "stm32-ddr-phy-binary" "$DDRFW_REPO" "$DDRFW_BRANCH" "$DDRFW_REV" "$DDRFW_SRC"
  need_file "$DDRFW_SRC/stm32mp2/lpddr4_pmu_train.bin"
}

# -----------------------------------------------------------------------------
do_optee() {
  use_toolchain elf
  need_cmd python3 cmake
  section "OP-TEE OS $OPTEE_BRANCH for $OPTEE_PLATFORM ($OPTEE_DTS)"
  explain "OP-TEE is the trusted OS. Besides running trusted applications it is, on this" \
          "SoC, the SCMI server: Linux asks it (through the secure monitor) to enable" \
          "clocks and release resets that only the secure world may touch."
  git_checkout "optee_os" "$OPTEE_REPO" "$OPTEE_BRANCH" "$OPTEE_REV" "$OPTEE_SRC"
  apply_patches optee "$OPTEE_SRC"
  # supported-ta-targets is "ta_arm64" for stm32mp2 (core/arch/arm/plat-stm32mp2/conf.mk),
  # so no 32-bit compiler is needed. CFG_EMBED_DTB_SOURCE_FILE picks the board's
  # device tree, which is compiled into the OP-TEE image: it tells the secure OS
  # which peripherals it owns (RIF/firewall setup, SCMI clocks, UART...).
  local optee_args=(O="$OPTEE_OUT" ARCH=arm PLATFORM="$OPTEE_PLATFORM"
                    CFG_EMBED_DTB_SOURCE_FILE="$OPTEE_DTS" CFG_TEE_CORE_LOG_LEVEL=2)
  if [[ $STACK == st ]]; then
    # STACK=st: ST's OP-TEE 4.0 names its compilers differently and brings its own copy of the
    # SCMI server, so there is no scp-firmware to fetch. ST's device trees come with CFG_EXT_DTS
    # (in OPTEE_EXTRA_FLAGS). The font generator of the user-space libraries needs python3-pil.
    checkout_extdt
    optee_args+=(CFG_ARM64_core=y CROSS_COMPILE_core="$CROSS_COMPILE" CROSS_COMPILE_ta_arm64="$CROSS_COMPILE")
    # shellcheck disable=SC2206  # the flags are a space separated list on purpose
    optee_args+=($OPTEE_EXTRA_FLAGS)
  else
    # OP-TEE's SCMI server is Arm's SCP-firmware, compiled into the OP-TEE core.
    # CFG_SCP_FIRMWARE must point at its source tree (OP-TEE refuses to build otherwise).
    git_checkout "scp-firmware" "$SCPFW_REPO" "$SCPFW_BRANCH" "$SCPFW_REV" "$SCPFW_SRC"
    optee_args+=(CROSS_COMPILE64="$CROSS_COMPILE" CFG_SCP_FIRMWARE="$SCPFW_SRC")
  fi
  run "Build OP-TEE core (plain make, not run_make: it must not get ARCH=arm64)" \
    make -C "$OPTEE_SRC" -j"$JOBS" "${optee_args[@]}" all
  if [[ $DRY_RUN != 1 ]]; then
    local f
    mkdir -p "$DEPLOY_DIR"
    # tee-pageable_v2.bin is empty (paging is off) and only ST's FIP lists it.
    for f in tee-header_v2.bin tee-pager_v2.bin tee-pageable_v2.bin; do
      cp "$OPTEE_OUT/core/$f" "$DEPLOY_DIR/$f"
    done
    info "OP-TEE: $(hsize "$DEPLOY_DIR/tee-pager_v2.bin") pager image in $DEPLOY_DIR"
  fi
}

# -----------------------------------------------------------------------------
uboot_fetch() {
  git_checkout "u-boot" "$UBOOT_REPO" "$UBOOT_BRANCH" "$UBOOT_REV" "$UBOOT_SRC"
  apply_patches u-boot "$UBOOT_SRC"
}

do_uboot_cfg() {
  use_toolchain linux
  section "U-Boot $UBOOT_BRANCH ($UBOOT_DEFCONFIG)"
  uboot_fetch
  if [[ -f $UBOOT_OUT/.config && ${FORCE_CONFIG:-0} != 1 ]]; then
    info "Keeping existing U-Boot .config (FORCE_CONFIG=1 to regenerate)"
  else
    run "Create the output directory" mkdir -p "$UBOOT_OUT"
    MAKE_ARCH=arm run_make "Create U-Boot's .config from configs/$UBOOT_DEFCONFIG" "$UBOOT_SRC" O="$UBOOT_OUT" "$UBOOT_DEFCONFIG"
  fi
}

do_uboot() {
  do_uboot_cfg
  explain "U-Boot here is BL33: BL2 loads it into DRAM and BL31 starts it in the normal world." \
          "TF-A wants two files from it: u-boot-nodtb.bin (the program) and u-boot.dtb" \
          "(its own device tree, passed as BL33_CFG)." \
          "(U-Boot calls the whole ARM family ARCH=arm, 64-bit included.)"
  # STACK=st: the board's device tree is not in U-Boot's tree but in ST's dt-stm32mp repository.
  # EXT_DTS names that directory, DEVICE_TREE_EXT the tree to use (both in UBOOT_EXTRA_FLAGS).
  [[ $STACK != st ]] || checkout_extdt
  local uboot_args=(DEVICE_TREE="$UBOOT_DEVICE_TREE")
  # shellcheck disable=SC2206  # the flags are a space separated list on purpose
  uboot_args+=($UBOOT_EXTRA_FLAGS)
  MAKE_ARCH=arm run_make "Compile U-Boot for the $UBOOT_DEVICE_TREE device tree" "$UBOOT_SRC" O="$UBOOT_OUT" \
    "${uboot_args[@]}" all
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
    PLAT="$TFA_PLATFORM" CROSS_COMPILE="$CROSS_COMPILE"
    DTB_FILE_NAME="$TFA_DTB" "$TFA_DDR_TYPE_FLAG" "$TFA_BOOT_FLAG"
    SPD="$TFA_SPD" LOG_LEVEL="$TFA_LOG_LEVEL"
    BUILD_BASE="$TFA_OUT"
    STM32MP_DDR_FW_PATH="$DDRFW_SRC/stm32mp2"
  )
  # STACK=st adds (config/stack-st.conf): PSA_FWU_SUPPORT=1 (BL2 reads the FWU metadata),
  # TFA_EXTERNAL_DT (ST's TF-A device trees) and DEBUG=1 (ST's "debug trace" build).
  # shellcheck disable=SC2206  # the flags are a space separated list on purpose
  TFA_ARGS+=($TFA_EXTRA_FLAGS)
}

do_tfa() {
  use_toolchain elf
  need_cmd dtc
  section "TF-A $TFA_BRANCH for $TFA_PLATFORM / $TFA_DTB"
  git_checkout "trusted-firmware-a" "$TFA_REPO" "$TFA_BRANCH" "$TFA_REV" "$TFA_SRC"
  apply_patches tf-a "$TFA_SRC"
  [[ $STACK != st ]] || checkout_extdt
  tfa_args
  explain "BL2 is linked to run from the SoC's internal SRAM (0x0E016000) and gets an" \
          "STM32 image header (the Boot ROM checks it) -> $BL2_NAME." \
          "BL31 is the secure monitor that stays resident after boot."
  run "Build BL2 (+STM32 header) and BL31" \
    make -C "$TFA_SRC" -j"$JOBS" "${TFA_ARGS[@]}" all
  if [[ $DRY_RUN != 1 ]]; then
    mkdir -p "$DEPLOY_DIR"
    cp "$TFA_BUILD/$BL2_NAME" "$DEPLOY_DIR/$BL2_NAME"
    info "BL2: $(hsize "$DEPLOY_DIR/$BL2_NAME") -> $DEPLOY_DIR/$BL2_NAME"
  fi
}

# STACK=st: ST's TF-A has no `make fip` for this chip, so the FIP is packed by calling the
# fiptool directly, with the file list ST's own packaging script uses (create_st_fip_binary.sh
# in meta-st-stm32mp). fiptool needs ST's platform helper to know the STM32MP2 UUID names.
do_fip_st() {
  need_cmd dtc
  section "FIP (ST): pack BL31 + OP-TEE + U-Boot + DDR firmware"
  local fdts="$TFA_BUILD/fdts" fiptool="$TFA_SRC/tools/fiptool/fiptool"
  need_file "$DEPLOY_DIR/tee-header_v2.bin" "$DEPLOY_DIR/tee-pager_v2.bin" "$DEPLOY_DIR/tee-pageable_v2.bin" \
            "$DEPLOY_DIR/u-boot-nodtb.bin" "$DEPLOY_DIR/u-boot.dtb" \
            "$DDRFW_SRC/stm32mp2/lpddr4_pmu_train.bin" "$TFA_BUILD/bl31.bin" "$fdts/$EXTDT_NAME-fw-config.dtb"
  explain "Same idea as the mainline FIP: a table of contents with one UUID per image, then the images." \
          "BL2 finds them by UUID: fw-config tells it where everything goes, BL31 + its DTB,"  \
          "OP-TEE (header = BL32, pager = BL32_EXTRA1; the pageable part is empty), U-Boot (BL33)" \
          "and its DTB (HW_CONFIG), and the DDR training firmware."
  run "Build fiptool with ST's platform helper (it knows the STM32MP2 image names)" \
    make -C "$TFA_SRC" PLAT_FIPTOOL_HELPER_MK=plat_fiptool/st/stm32mp2/plat_fiptool.mk \
      PLAT_DIR=../../plat/st/stm32mp2 fiptool
  run "Pack the FIP" "$fiptool" create \
    --fw-config "$fdts/$EXTDT_NAME-fw-config.dtb" \
    --soc-fw "$TFA_BUILD/bl31.bin" --soc-fw-config "$fdts/$EXTDT_NAME-bl31.dtb" \
    --ddr-fw "$DDRFW_SRC/stm32mp2/lpddr4_pmu_train.bin" \
    --tos-fw "$DEPLOY_DIR/tee-header_v2.bin" --tos-fw-extra1 "$DEPLOY_DIR/tee-pager_v2.bin" \
    --tos-fw-extra2 "$DEPLOY_DIR/tee-pageable_v2.bin" \
    --nt-fw "$DEPLOY_DIR/u-boot-nodtb.bin" --hw-config "$DEPLOY_DIR/u-boot.dtb" \
    "$DEPLOY_DIR/fip.bin"
  if [[ $DRY_RUN != 1 ]]; then
    cp "$TFA_BUILD/$BL2_NAME" "$DEPLOY_DIR/$BL2_NAME"
    run "List what is inside the FIP" "$fiptool" info "$DEPLOY_DIR/fip.bin"
    local fip_max=$(( FIP_SIZE_KB * 1024 ))
    (( $(stat -c %s "$DEPLOY_DIR/fip.bin") <= fip_max )) ||
      die "fip.bin is larger than the ${FIP_SIZE_KB} KiB FIP partition; raise FIP_SIZE_KB"
    info "FIP: $(hsize "$DEPLOY_DIR/fip.bin") of ${FIP_SIZE_KB} KiB partition"
  fi
}

# STACK=st: with PSA_FWU_SUPPORT=1 BL2 does not look for "the" FIP partition. It reads a small
# metadata record that names the FIP partition of each of two banks (fip-a, fip-b) and says which
# bank is active. mkfwumdata is a host tool in U-Boot's tree (tools-only build).
do_metadata() {
  use_toolchain linux
  section "FWU metadata: bank 0 = fip-a is active"
  uboot_fetch
  explain "mkfwumdata writes metadata.bin: 1 image per bank, 2 banks, version 2, bank 0 active." \
          "The UUIDs are, in order: the GUID of the metadata partition type, the GUID of the FIP" \
          "partition type, then the PARTUUIDs of fip-a and fip-b (image.sh gives the partitions" \
          "exactly those PARTUUIDs; ST's own image does the same)."
  run "Create the output directory" mkdir -p "$UBOOT_OUT-tools"
  MAKE_ARCH=arm run_make "Configure U-Boot's host tools only" "$UBOOT_SRC" O="$UBOOT_OUT-tools" tools-only_defconfig
  MAKE_ARCH=arm run_make "Build U-Boot's host tools (mkfwumdata, mkimage...)" "$UBOOT_SRC" O="$UBOOT_OUT-tools" tools-only
  run "Write the metadata" "$UBOOT_OUT-tools/tools/mkfwumdata" -g -i 1 -b 2 -v 2 \
    "$FWU_METADATA_GUID,${GUID_ST_FIP,,},$FIP_A_PARTUUID,$FIP_B_PARTUUID" "$DEPLOY_DIR/metadata.bin"
  if [[ $DRY_RUN != 1 ]]; then
    (( $(stat -c %s "$DEPLOY_DIR/metadata.bin") <= META_SIZE_KB * 1024 )) ||
      die "metadata.bin does not fit the ${META_SIZE_KB} KiB metadata partitions"
    info "FWU metadata: $(hsize "$DEPLOY_DIR/metadata.bin") -> $DEPLOY_DIR/metadata.bin"
  fi
}

do_fip() {
  [[ $STACK != st ]] || { do_fip_st; return; }
  use_toolchain elf
  need_cmd dtc
  section "FIP: pack BL31 + OP-TEE + U-Boot + DDR firmware"
  tfa_args
  need_file "$DEPLOY_DIR/tee-header_v2.bin" "$DEPLOY_DIR/tee-pager_v2.bin" \
            "$DEPLOY_DIR/u-boot-nodtb.bin" "$DEPLOY_DIR/u-boot.dtb" \
            "$DDRFW_SRC/stm32mp2/lpddr4_pmu_train.bin"
  explain "fiptool (built from TF-A's tools/fiptool) writes a table of contents with a" \
          "UUID per image, then the images back to back. BL2 looks the images up by UUID:" \
          "  BL32 = OP-TEE header (28 bytes), BL32_EXTRA1 = the OP-TEE image itself (--tos-fw-extra1)," \
          "  BL33 = U-Boot, BL33_CFG = U-Boot's DTB (--hw-config)." \
          "tee-pageable_v2.bin is empty here (OP-TEE's paging is off), so it is not packed."
  run "Build the FIP" \
    make -C "$TFA_SRC" -j"$JOBS" "${TFA_ARGS[@]}" \
      BL33="$DEPLOY_DIR/u-boot-nodtb.bin" BL33_CFG="$DEPLOY_DIR/u-boot.dtb" \
      BL32="$DEPLOY_DIR/tee-header_v2.bin" \
      BL32_EXTRA1="$DEPLOY_DIR/tee-pager_v2.bin" \
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
  MAKE_ARCH=arm run_make "Open U-Boot's interactive configuration menu" "$UBOOT_SRC" O="$UBOOT_OUT" menuconfig
  info "Your changes are in $UBOOT_OUT/.config. To keep them, save a fragment in patches/ (see docs/08)."
}

do_clean() {
  section "Cleaning firmware build outputs (sources and downloads are kept)"
  run "Remove the out-of-tree build directories" rm -rf "$TFA_OUT" "$OPTEE_OUT" "$UBOOT_OUT" "$UBOOT_OUT-tools"
  run "Remove the deployed firmware files" rm -f "$DEPLOY_DIR"/tf-a-*.stm32 "$DEPLOY_DIR"/fip.bin \
    "$DEPLOY_DIR"/tee-*_v2.bin "$DEPLOY_DIR"/u-boot-nodtb.bin "$DEPLOY_DIR"/u-boot.dtb \
    "$DEPLOY_DIR"/metadata.bin
}

main() {
  local target=${1:-all}
  [[ $target == menuconfig ]] || start_log "firmware-$target"
  case $target in
    all)        do_ddr; do_optee; do_uboot; do_tfa; do_fip; [[ $STACK != st ]] || do_metadata ;;
    ddr)        do_ddr ;;
    optee)      do_optee ;;
    uboot)      do_uboot ;;
    tfa)        do_tfa ;;
    fip)        do_fip ;;
    metadata)   [[ $STACK == st ]] || die "the metadata step exists only for STACK=st"; do_metadata ;;
    menuconfig) do_menuconfig ;;
    clean)      do_clean ;;
    *) die "unknown target '$target' (all|ddr|optee|uboot|tfa|fip|metadata|menuconfig|clean)" ;;
  esac
}

main "$@"
