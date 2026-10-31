#!/usr/bin/env bash
# =============================================================================
#  build.sh - one entry point for the whole STM32MP157F-DK2 build
# =============================================================================
#
#  ./build.sh all                 boot firmware + kernel + rootfs + SD card image
#  ./build.sh flash -d /dev/sdX   write the image to an SD card
#
#  Run ./build.sh help for everything else. Each step is a standalone script
#  in scripts/ that you can also call directly.
# =============================================================================
set -Eeuo pipefail
TOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/common.sh
source "$TOP_DIR/scripts/lib/common.sh"

usage() {
  cat <<EOF
${C_BOLD}Usage:${C_RESET} ./build.sh [options] <command> [command args]

${C_BOLD}Main commands${C_RESET}
  all                 Build everything and assemble the SD card image
                      (= firmware + kernel + rootfs + image)
  flash -d /dev/sdX   Write build/deploy/sdcard.img to an SD card (sudo)
        [--expand]        ...and grow the root partition to the whole card
        [--firmware-only | --kernel-only]   update just that part

${C_BOLD}Individual steps${C_RESET}
  deps [--install]    Check (or apt-install) the host packages needed
  firmware [step]     Boot chain: optee | uboot | tfa | fip | all (default)
  kernel [step]       Kernel: config | build | install | all (default)
  rootfs              Root filesystem tarball (see --rootfs)
  image               Assemble build/deploy/sdcard.img from the parts above

${C_BOLD}Configuration & maintenance${C_RESET}
  info                Show the versions/refs that will be built
  uboot-menuconfig    Interactive U-Boot configuration
  kernel-menuconfig   Interactive kernel configuration
  clean               Remove build outputs, keep downloads and sources
  distclean           Remove the whole build/ directory

${C_BOLD}Options${C_RESET} (before the command)
  -n, --dry-run       EXPLAIN MODE: print every command with a comment saying
                      why it is needed, without running anything
  -v, --verbose       Show full compiler command lines (make V=1)
  -j, --jobs N        Parallel jobs (default: $(nproc))
  -u, --update        Re-fetch the pinned git sources (refuses if you have
                      uncommitted local changes in them)
  -r, --rootfs X      debian | alpine | /path/to/rootfs.tar.* (default: debian)
  -y, --yes           Do not ask for confirmations
  -h, --help          This help

${C_BOLD}Examples${C_RESET}
  ./build.sh deps --install                # once, on a fresh Ubuntu/Debian PC
  ./build.sh all                           # full build with a Debian rootfs
  ./build.sh -r alpine all                 # quick build, tiny rootfs, no sudo
  ./build.sh flash -d /dev/sdb --expand    # write it and use the whole card
  ./build.sh --dry-run firmware            # read how the boot chain is built
  ./build.sh firmware fip                  # re-pack only the FIP

Docs: README.md and docs/
EOF
}

# -----------------------------------------------------------------------------
# Host dependencies (Debian / Ubuntu package names)
# -----------------------------------------------------------------------------
HOST_PACKAGES=(
  # generic build tools
  build-essential git make bc bison flex libssl-dev libncurses-dev libelf-dev
  # U-Boot host tools (mkimage, device tree compiler, binman), TF-A's fiptool,
  # and OP-TEE's build scripts (python3 + pyelftools)
  libgnutls28-dev uuid-dev python3 python3-dev python3-setuptools
  python3-pyelftools swig device-tree-compiler
  # kernel modules_install (depmod) and packing
  kmod cpio rsync xz-utils zstd
  # downloads
  wget ca-certificates
  # SD card image creation (rootless)
  fakeroot e2fsprogs fdisk bmap-tools openssl
  # Debian root filesystem (armhf binaries run through qemu during bootstrap:
  # an x86 PC and most ARM64 PCs cannot execute 32-bit ARM code natively)
  mmdebstrap arch-test qemu-user-static binfmt-support uidmap
  # faster rebuilds
  ccache
)

cmd_deps() {
  section "Host dependencies"
  command -v dpkg-query >/dev/null || die "automatic check only works on Debian/Ubuntu; install the equivalents of: ${HOST_PACKAGES[*]}"
  local missing=() p
  for p in "${HOST_PACKAGES[@]}"; do
    dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "ok installed" || missing+=("$p")
  done
  if ((${#missing[@]} == 0)); then
    info "All ${#HOST_PACKAGES[@]} host packages are installed."
    return 0
  fi
  warn "Missing packages: ${missing[*]}"
  if [[ ${1:-} == --install ]]; then
    run "Refresh the package lists" sudo apt-get update
    run "Install the missing host packages" sudo apt-get install -y "${missing[@]}"
  else
    echo "  Install them with:"
    echo "    sudo apt-get install -y ${missing[*]}"
    echo "  or run: ./build.sh deps --install"
  fi
}

cmd_info() {
  cat <<EOF
${C_BOLD}BSP release${C_RESET}   $BSP_RELEASE  (board: $BOARD_NAME)
${C_BOLD}TF-A${C_RESET}          $TFA_REPO
              ref $TFA_BRANCH  rev ${TFA_REV:-<ref head>}
              PLAT=$TFA_PLATFORM DTB=$TFA_DTB $TFA_BOOT_FLAG $TFA_SPD
${C_BOLD}OP-TEE${C_RESET}        $OPTEE_REPO
              ref $OPTEE_BRANCH  rev ${OPTEE_REV:-<ref head>}
              PLATFORM=$OPTEE_PLATFORM dts $OPTEE_DTS
${C_BOLD}U-Boot${C_RESET}        $UBOOT_REPO
              ref $UBOOT_BRANCH  rev ${UBOOT_REV:-<ref head>}
              defconfig $UBOOT_DEFCONFIG, DEVICE_TREE=$UBOOT_DEVICE_TREE
${C_BOLD}Kernel${C_RESET}        Linux $KERNEL_VERSION (kernel.org tarball)
              defconfig $KERNEL_DEFCONFIG + config/kernel/*.cfg, image $KERNEL_IMAGE, DTBs: $KERNEL_DTBS
${C_BOLD}Toolchain${C_RESET}     $TOOLCHAIN$( [[ $TOOLCHAIN == arm ]] && echo " (Arm GNU Toolchain $ARM_TOOLCHAIN_VERSION: arm-none-eabi + arm-none-linux-gnueabihf)")
${C_BOLD}Rootfs${C_RESET}        $ROOTFS$( [[ $ROOTFS == debian ]] && echo " ($DEBIAN_SUITE $DEBIAN_ARCH)")$( [[ $ROOTFS == alpine ]] && echo " ($ALPINE_VERSION $ALPINE_ARCH)")
${C_BOLD}Console${C_RESET}       $TARGET_CONSOLE at $CONSOLE_BAUD baud
${C_BOLD}Build dir${C_RESET}     $BUILD_DIR
EOF
}

cmd_clean() {
  section "Cleaning build outputs (keeping downloads, toolchains and sources)"
  "$TOP_DIR/scripts/firmware.sh" clean
  "$TOP_DIR/scripts/kernel.sh" clean
  run "Remove intermediate files and deployed artifacts" rm -rf "$WORK_DIR" "$DEPLOY_DIR"
}

cmd_distclean() {
  confirm "Delete $BUILD_DIR entirely (sources, downloads, toolchains, outputs)?" || die "aborted"
  run "Remove everything generated" rm -rf "$BUILD_DIR"
}

# -----------------------------------------------------------------------------
# Option parsing. Options are exported so the step scripts inherit them.
# -----------------------------------------------------------------------------
while (($#)); do
  case $1 in
    -n|--dry-run)  export DRY_RUN=1 ;;
    -v|--verbose)  export VERBOSE=1 ;;
    -j|--jobs)     export JOBS=$2; shift ;;
    -u|--update)   export UPDATE=1 ;;
    -r|--rootfs)   export ROOTFS=$2 ROOTFS_EXPLICIT=1; shift ;;
    -y|--yes)      export ASSUME_YES=1 ;;
    -h|--help|help) usage; exit 0 ;;
    -*) usage; die "unknown option: $1" ;;
    *) break ;;
  esac
  shift
done

(($#)) || { usage; exit 1; }
load_config
cmd=$1; shift
S="$TOP_DIR/scripts"

case $cmd in
  all)
    [[ $DRY_RUN == 1 ]] || check_disk_space 15
    started=$SECONDS
    "$S/firmware.sh" all
    "$S/kernel.sh" all
    # Re-use an existing rootfs tarball; it rarely changes and Debian takes a while.
    if [[ -e $DEPLOY_DIR/rootfs.tar && ${REBUILD_ROOTFS:-0} != 1 && -z ${ROOTFS_EXPLICIT:-} ]]; then
      info "Re-using $(readlink "$DEPLOY_DIR/rootfs.tar") (run './build.sh rootfs' to rebuild it)"
    else
      "$S/rootfs.sh"
    fi
    "$S/image.sh"
    info "Everything built in $(( (SECONDS - started) / 60 )) min $(( (SECONDS - started) % 60 )) s"
    ;;
  deps)              cmd_deps "$@" ;;
  info)              cmd_info ;;
  firmware)          "$S/firmware.sh" "${1:-all}" ;;
  uboot-menuconfig)  "$S/firmware.sh" menuconfig ;;
  kernel)            "$S/kernel.sh" "${1:-all}" ;;
  kernel-menuconfig) "$S/kernel.sh" menuconfig ;;
  rootfs)            "$S/rootfs.sh" ;;
  image)             "$S/image.sh" ;;
  flash)             "$S/flash.sh" "$@" ;;
  clean)             cmd_clean ;;
  distclean)         cmd_distclean ;;
  *) usage; die "unknown command: $cmd" ;;
esac
