#!/usr/bin/env bash
# =============================================================================
#  scripts/fetch.sh - download NVIDIA's Jetson Linux release (checksummed)
# =============================================================================
#
#  Nothing here is built from a git repository: NVIDIA publishes Jetson Linux
#  as release archives. Four files, all cached in build/downloads/:
#
#    bsp        Jetson_Linux_r36.4.3_aarch64.tbz2         715 MB  flash tools,
#                                                          firmware, prebuilt kernel
#    rootfs     Tegra_Linux_Sample-Root-Filesystem_…tbz2  1.8 GB  Ubuntu 22.04 userland
#    sources    public_sources.tbz2                       226 MB  kernel, modules, DTS
#    toolchain  aarch64--glibc--stable-2022.08-1.tar.bz2  140 MB  reference gcc 11.3
#
#  sources and toolchain are only needed to build your own kernel; with
#  --stock-kernel they are skipped.
#
#  Usage: scripts/fetch.sh [all|bsp|rootfs|sources|toolchain]
#         (normally called through ./build.sh fetch)
# =============================================================================
# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
strict_mode
load_config

: "${STOCK_KERNEL:=0}"

main() {
  local target=${1:-all}
  start_log "fetch"
  section "Jetson Linux R$L4T_RELEASE downloads"
  explain "These files are governed by NVIDIA's Tegra Software License Agreement" \
          "(Linux_for_Tegra/Tegra_Software_License_Agreement-Tegra-Linux.txt after" \
          "unpacking, or $L4T_URL_BASE/release/tegra_software_license_agreement-tegra-linux.txt)." \
          "Each download is verified against a pinned sha256."
  case $target in
    bsp)       fetch "$BSP_URL" "$DL_DIR/$BSP_FILE" "$BSP_SHA256" ;;
    rootfs)    fetch "$ROOTFS_URL" "$DL_DIR/$ROOTFS_FILE" "$ROOTFS_SHA256" ;;
    sources)   fetch "$SOURCES_URL" "$DL_DIR/$SOURCES_FILE" "$SOURCES_SHA256" ;;
    toolchain) fetch "$TOOLCHAIN_URL" "$DL_DIR/$TOOLCHAIN_FILE" "$TOOLCHAIN_SHA256" ;;
    all)
      fetch "$BSP_URL" "$DL_DIR/$BSP_FILE" "$BSP_SHA256"
      fetch "$ROOTFS_URL" "$DL_DIR/$ROOTFS_FILE" "$ROOTFS_SHA256"
      if [[ $STOCK_KERNEL == 1 ]]; then
        info "--stock-kernel: skipping the kernel sources and the cross compiler"
      else
        fetch "$SOURCES_URL" "$DL_DIR/$SOURCES_FILE" "$SOURCES_SHA256"
        fetch "$TOOLCHAIN_URL" "$DL_DIR/$TOOLCHAIN_FILE" "$TOOLCHAIN_SHA256"
      fi
      ;;
    *) die "unknown target '$target' (all|bsp|rootfs|sources|toolchain)" ;;
  esac
  [[ $DRY_RUN == 1 ]] || info "Downloads are in $DL_DIR"
}

main "$@"
