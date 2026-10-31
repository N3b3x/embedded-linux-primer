#!/usr/bin/env bash
# =============================================================================
#  build.sh - one entry point for the NVIDIA Jetson Orin Nano build
# =============================================================================
#
#  ./build.sh --accept-license all      download, rootfs, kernel, flash package
#  ./build.sh flash                     flash the board over USB (recovery mode)
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
  all                 fetch + rootfs + kernel + image  (nothing is written to the board)
  flash               Flash the board over USB; it must be in Force Recovery Mode (sudo)
        [--full]          ...regenerate the flash package first
        [--check]         ...only look for a board in recovery mode

${C_BOLD}Individual steps${C_RESET}
  deps [--install]    Check (or apt-install) the host packages needed
  fetch [what]        Download NVIDIA's release: bsp | rootfs | sources | toolchain | all
  rootfs              Unpack + assemble the root filesystem in Linux_for_Tegra/ (sudo)
  kernel [step]       Your own kernel: extract | config | build | install | all (default)
  image [--offline]   Generate the flash package, without touching a board (sudo)

${C_BOLD}Configuration & maintenance${C_RESET}
  info                Show the versions, URLs and the flash command that will be used
  kernel-menuconfig   Interactive kernel configuration
  clean               Remove the working tree and artifacts, keep downloads (sudo)
  distclean           Remove the whole build/ directory (sudo)

${C_BOLD}Options${C_RESET} (before the command)
  -n, --dry-run       EXPLAIN MODE: print every command with a comment saying
                      why it is needed, without running anything
  -b, --board X       Board config: jetson-orin-nano-devkit-super (default) |
                      jetson-orin-nano-devkit
  -d, --root-device X nvme (default) | sd | usb : where the OS is written
      --stock-kernel  Use NVIDIA's prebuilt kernel: skips the toolchain and the
                      kernel compile (a good first run)
  -v, --verbose       Show full compiler command lines (make V=1)
  -j, --jobs N        Parallel jobs (default: $(nproc 2>/dev/null || echo 4))
  -u, --update        Throw away and re-extract the kernel sources
      --accept-license  Accept NVIDIA's Tegra Software License Agreement
  -y, --yes           Do not ask for confirmations
  -h, --help          This help

${C_BOLD}Examples${C_RESET}
  ./build.sh deps --install                       # once, on Ubuntu 22.04 x86-64
  ./build.sh --accept-license --stock-kernel all  # first run: NVIDIA's own kernel
  ./build.sh --accept-license all                 # ...or with a kernel built from source
  ./build.sh -d sd flash                          # microSD card as the root device
  ./build.sh --dry-run kernel | less -R           # read how the kernel is built

Docs: README.md and docs/
EOF
}

# -----------------------------------------------------------------------------
# Host dependencies (Ubuntu / Debian package names)
#   the first block is NVIDIA's own list: Linux_for_Tegra/tools/l4t_flash_prerequisites.sh
#   the second block is what building a kernel needs
# -----------------------------------------------------------------------------
HOST_PACKAGES=(
  # NVIDIA's flash prerequisites (l4t_flash_prerequisites.sh, R36.4.3)
  abootimg binfmt-support binutils cpio cpp device-tree-compiler dosfstools
  iproute2 iputils-ping lbzip2 libxml2-utils netcat-openbsd nfs-kernel-server openssl
  python3-yaml qemu-user-static rsync sshpass udev uuid-runtime whois xmlstarlet zstd lz4
  # kernel build, downloads, USB inspection
  build-essential bc bison flex libssl-dev libncurses-dev libelf-dev kmod patch
  wget ca-certificates usbutils
)

cmd_deps() {
  section "Host dependencies"
  host_check
  if [[ -r /etc/os-release ]]; then
    # shellcheck source=/dev/null
    . /etc/os-release
    case ${VERSION_ID:-} in
      20.04|22.04) info "Host: $PRETTY_NAME (named by NVIDIA for Jetson Linux R$L4T_RELEASE)" ;;
      *) warn "Host: ${PRETTY_NAME:-unknown}. NVIDIA's Quick Start names Ubuntu 20.04 and 22.04; other releases may work, but are not what the tools were documented for." ;;
    esac
  fi
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
  initrd_flash_args
  cat <<EOF
${C_BOLD}Release${C_RESET}       Jetson Linux R$L4T_RELEASE (JetPack 6.2, kernel 5.15 "-tegra")
${C_BOLD}Driver pkg${C_RESET}     $BSP_FILE
              $BSP_URL
              sha256 $BSP_SHA256
${C_BOLD}Sample rootfs${C_RESET}  $ROOTFS_FILE
              sha256 $ROOTFS_SHA256
${C_BOLD}Sources${C_RESET}        $SOURCES_FILE
              sha256 $SOURCES_SHA256
${C_BOLD}Toolchain${C_RESET}      $TOOLCHAIN_TOP (Bootlin, GCC 11.3, x86-64 host only)
              sha256 $TOOLCHAIN_SHA256
${C_BOLD}Board${C_RESET}          $BOARD   (file Linux_for_Tegra/$BOARD.conf)
${C_BOLD}Root device${C_RESET}    $ROOT_DEVICE -> /dev/$(external_device) on the board
${C_BOLD}Layouts${C_RESET}        QSPI  $QSPI_LAYOUT
              ext.  $EXT_LAYOUT
${C_BOLD}Flash cmd${C_RESET}      sudo env ${INITRD_ENV[*]:-} ./tools/kernel_flash/l4t_initrd_flash.sh $(quote_cmd "${INITRD_ARGS[@]}") $BOARD internal
${C_BOLD}Default user${C_RESET}   $TARGET_USER @ $TARGET_HOSTNAME
${C_BOLD}Work tree${C_RESET}      $L4T_DIR
${C_BOLD}Build dir${C_RESET}      $BUILD_DIR
EOF
}

cmd_clean() {
  section "Cleaning build outputs (keeping downloads and the toolchain)"
  explain "The working tree contains files owned by root (the rootfs), so removing it needs sudo."
  run "Remove the Linux_for_Tegra working tree and the artifacts" sudo rm -rf "$WORK_DIR" "$DEPLOY_DIR"
}

cmd_distclean() {
  confirm "Delete $BUILD_DIR entirely (downloads, toolchain, working tree, outputs)?" || die "aborted"
  run "Remove everything generated" sudo rm -rf "$BUILD_DIR"
}

# -----------------------------------------------------------------------------
# Option parsing. Options are exported so the step scripts inherit them.
# -----------------------------------------------------------------------------
while (($#)); do
  case $1 in
    -n|--dry-run)       export DRY_RUN=1 ;;
    -v|--verbose)       export VERBOSE=1 ;;
    -j|--jobs)          export JOBS=$2; shift ;;
    -u|--update)        export UPDATE=1 ;;
    -b|--board)         export BOARD=$2; shift ;;
    -d|--root-device)   export ROOT_DEVICE=$2; shift ;;
    --stock-kernel)     export STOCK_KERNEL=1 ;;
    --accept-license)   export ACCEPT_LICENSE=1 ;;
    -y|--yes)           export ASSUME_YES=1 ;;
    -h|--help|help)     usage; exit 0 ;;
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
    [[ $DRY_RUN == 1 ]] || check_disk_space 60
    started=$SECONDS
    "$S/fetch.sh" all
    "$S/rootfs.sh"
    if [[ ${STOCK_KERNEL:-0} == 1 ]]; then
      info "--stock-kernel: keeping NVIDIA's prebuilt kernel from the driver package"
    else
      "$S/kernel.sh" all
    fi
    "$S/image.sh"
    info "Everything built in $(( (SECONDS - started) / 60 )) min $(( (SECONDS - started) % 60 )) s"
    ;;
  deps)              cmd_deps "$@" ;;
  info)              cmd_info ;;
  fetch)             "$S/fetch.sh" "${1:-all}" ;;
  rootfs)            "$S/rootfs.sh" ;;
  kernel)            "$S/kernel.sh" "${1:-all}" ;;
  kernel-menuconfig) "$S/kernel.sh" menuconfig ;;
  image)             "$S/image.sh" "$@" ;;
  flash)             "$S/flash.sh" "$@" ;;
  clean)             cmd_clean ;;
  distclean)         cmd_distclean ;;
  *) usage; die "unknown command: $cmd" ;;
esac
