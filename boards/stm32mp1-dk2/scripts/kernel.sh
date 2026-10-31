#!/usr/bin/env bash
# =============================================================================
#  scripts/kernel.sh - build the Linux kernel, device tree and modules
# =============================================================================
#
#  Output is a small "overlay" directory tree that is merged on top of the root
#  filesystem when the SD card image is assembled:
#
#    build/deploy/kernel/
#      boot/zImage                     <- extlinux.conf: "LINUX /boot/zImage"
#      boot/stm32mp157f-dk2.dtb        <- extlinux.conf: "FDT /boot/stm32mp157f-dk2.dtb"
#      boot/config-<version>           <- the .config this kernel was built from
#      lib/modules/<version>/...       <- loadable drivers (modprobe)
#    build/deploy/kernel-<version>.tar.gz  (same thing, to update an existing card)
#
#  The kernel is a stable release tarball from kernel.org, not a git checkout:
#  150 MB instead of several GB, and the sha256 in the config file pins it.
#
#  Usage: scripts/kernel.sh [all|config|build|install|menuconfig|clean]
# =============================================================================
# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
strict_mode
load_config

KSRC="$SRC_DIR/linux-$KERNEL_VERSION"
KDTS="$KSRC/arch/arm/boot/dts/st"
OVERLAY="$DEPLOY_DIR/kernel"
CUSTOM_DTS_DIR="$TOP_DIR/custom/dts"
FRAGMENT_DIR="$TOP_DIR/config/kernel"

# Every make call gets the same LOCALVERSION, otherwise the version string of
# the Image and of /lib/modules/<version> could differ and modules won't load.
kmake() { run_make "$1" "$KSRC" LOCALVERSION="$KERNEL_LOCALVERSION" "${@:2}"; }

# -----------------------------------------------------------------------------
fetch_sources() {
  section "Linux kernel source: $KERNEL_VERSION"
  local tarball="$DL_DIR/linux-$KERNEL_VERSION.tar.xz"
  fetch "$KERNEL_URL" "$tarball" "$KERNEL_SHA256"
  if [[ -d $KSRC ]]; then
    info "Using existing source tree $KSRC (delete it to unpack again)"
  else
    run "Create the source directory" mkdir -p "$SRC_DIR"
    run "Unpack the kernel source" tar -xJf "$tarball" -C "$SRC_DIR"
    apply_patches kernel "$KSRC"
  fi

  # Out-of-tree device trees: drop your *.dts / *.dtsi in custom/dts/ and
  # they are copied next to ST's files so they can #include them.
  if compgen -G "$CUSTOM_DTS_DIR/*.dts*" >/dev/null; then
    local f
    for f in "$CUSTOM_DTS_DIR"/*.dts*; do
      run "Copy custom device tree $(basename "$f") into the kernel tree" cp "$f" "$KDTS/"
    done
  fi
}

# -----------------------------------------------------------------------------
# Options without which the board cannot reach a login. They must be built in
# (=y), not modules: there is no initramfs, so the kernel has to read its root
# filesystem before it can load a single module. A fragment that switches one off
# by mistake would otherwise show up only as "VFS: Unable to mount root fs".
# Format: SYMBOL:why
REQUIRED_BUILTIN=(
  "ARCH_STM32:the STM32 SoC family"
  "MACH_STM32MP157:the STM32MP157 machine support"
  "COMMON_CLK_STM32MP157:the STM32MP15 clock controller (gates and dividers)"
  "PINCTRL_STM32MP157:the pin controller"
  "SERIAL_STM32:the ttySTM0 serial driver"
  "SERIAL_STM32_CONSOLE:console on ttySTM0"
  "MMC_ARMMMCI:the SD card controller (an ARM PL18x variant)"
  "MMC_STM32_SDMMC:ST's SDMMC variant of it"
  "REGULATOR_ARM_SCMI:regulators (the SD card's supply) served over SCMI"
  "EXT4_FS:the root filesystem"
  "EFI_PARTITION:GPT parsing, needed for root=PARTUUID="
  "DEVTMPFS:/dev"
  "DEVTMPFS_MOUNT:mount /dev before init"
  "TEE:the TEE subsystem OP-TEE plugs into"
  "OPTEE:the OP-TEE driver (the SCMI transport uses it)"
  "ARM_SCMI_PROTOCOL:the SCMI core"
  "ARM_SCMI_TRANSPORT_OPTEE:SCMI over OP-TEE"
  "COMMON_CLK_SCMI:clocks served over SCMI"
  "RESET_SCMI:resets served over SCMI"
  "REGULATOR_STM32_PWR:the SoC-internal PWR regulators the device tree refers to"
)

check_config() {
  [[ $DRY_RUN == 1 ]] && return 0
  local item sym why bad=0
  for item in "${REQUIRED_BUILTIN[@]}"; do
    sym=${item%%:*}; why=${item#*:}
    if ! grep -qx "CONFIG_$sym=y" "$KSRC/.config"; then
      warn "CONFIG_$sym is not built in: $why"
      bad=1
    fi
  done
  ((bad == 0)) || die "required kernel options are missing (see above); check config/kernel/*.cfg"
  info "All ${#REQUIRED_BUILTIN[@]} options the boot path needs are built in"
}

# -----------------------------------------------------------------------------
do_config() {
  use_toolchain linux
  fetch_sources
  section "Kernel configuration ($KERNEL_DEFCONFIG)"
  if [[ -f $KSRC/.config && ${FORCE_CONFIG:-0} != 1 ]]; then
    info "Keeping existing .config (run './build.sh kernel clean' or FORCE_CONFIG=1 to regenerate)"
    check_config
    return 0
  fi
  # arch/arm/configs/multi_v7_defconfig is the generic 32-bit ARMv7 configuration:
  # it covers many SoCs, STM32MP1 included (ARCH_STM32=y). Do not confuse it with
  # stm32_defconfig, which is for the Cortex-M microcontrollers.
  kmake "Create .config from arch/arm/configs/$KERNEL_DEFCONFIG" "$KERNEL_DEFCONFIG"

  # Optional config fragments: config/kernel/*.cfg, one CONFIG_FOO=y per line.
  if compgen -G "$FRAGMENT_DIR/*.cfg" >/dev/null; then
    run "Merge config fragments from config/kernel/ on top of the defconfig" \
      env ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" \
      "$KSRC/scripts/kconfig/merge_config.sh" -m -O "$KSRC" "$KSRC/.config" "$FRAGMENT_DIR"/*.cfg
    kmake "Resolve dependencies of the merged options (new symbols get defaults)" olddefconfig
  fi
  check_config
}

# -----------------------------------------------------------------------------
# Device tree targets: KERNEL_DTBS plus every custom/dts/*.dts
dtb_targets() {
  local list=() f
  for f in $KERNEL_DTBS; do list+=("${f%.dtb}.dtb"); done
  if compgen -G "$CUSTOM_DTS_DIR/*.dts" >/dev/null; then
    for f in "$CUSTOM_DTS_DIR"/*.dts; do list+=("st/$(basename "${f%.dts}").dtb"); done
  fi
  printf '%s\n' "${list[@]}" | sort -u
}

do_build() {
  [[ -f $KSRC/.config ]] || do_config
  use_toolchain linux
  section "Compiling kernel ($KERNEL_IMAGE + modules + device trees) with $JOBS jobs"
  explain "First build takes about 15 min on 12 cores; rebuilds only recompile what changed."
  kmake "Compile the kernel image and all modules" "$KERNEL_IMAGE" modules

  local dtbs=()
  mapfile -t dtbs < <(dtb_targets)
  ((${#dtbs[@]})) || die "no device trees selected (KERNEL_DTBS='$KERNEL_DTBS')"
  kmake "Compile ${#dtbs[@]} device tree(s) for the board" "${dtbs[@]}"
}

# -----------------------------------------------------------------------------
do_install() {
  use_toolchain linux
  section "Installing kernel into $OVERLAY"
  local kver
  if [[ $DRY_RUN == 1 ]]; then kver="<version>"; else
    kver=$(make -s -C "$KSRC" ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" LOCALVERSION="$KERNEL_LOCALVERSION" kernelrelease)
  fi
  info "Kernel release: $kver"

  run "Start from an empty overlay so removed files do not linger" rm -rf "$OVERLAY"
  run "Create /boot in the overlay" mkdir -p "$OVERLAY/boot"
  run "Install the kernel image" \
    cp "$KSRC/arch/arm/boot/$KERNEL_IMAGE" "$OVERLAY/boot/$KERNEL_IMAGE"
  run "Keep the matching .config for reference (also handy for out-of-tree modules)" \
    cp "$KSRC/.config" "$OVERLAY/boot/config-$kver"

  local d
  while read -r d; do
    run "Install device tree $(basename "$d")" cp "$KSRC/arch/arm/boot/dts/$d" "$OVERLAY/boot/"
  done < <(dtb_targets)

  # INSTALL_MOD_STRIP=1 strips debug symbols: ~10x smaller modules.
  # DEPMOD runs on the host to produce modules.dep etc. for the target.
  kmake "Install modules into <overlay>/lib/modules/$kver" modules_install \
    INSTALL_MOD_PATH="$OVERLAY" INSTALL_MOD_STRIP=1
  # The 'build' and 'source' links point into this PC; they are useless and
  # dangling on the board.
  run "Remove host-only build/source symlinks" \
    rm -f "$OVERLAY/lib/modules/$kver/build" "$OVERLAY/lib/modules/$kver/source"

  run "Pack the overlay as a tarball (to update an existing SD card in place)" \
    tar -C "$OVERLAY" --owner=0 --group=0 --mode=go-w -czf "$DEPLOY_DIR/kernel-$kver.tar.gz" .
  [[ $DRY_RUN == 1 ]] || ln -sfn "kernel-$kver.tar.gz" "$DEPLOY_DIR/kernel.tar.gz"
  [[ $DRY_RUN == 1 ]] || info "Kernel $kver installed: $(find "$OVERLAY"/boot -name '*.dtb' | wc -l) DTB(s), modules $(du -sh "$OVERLAY/lib/modules" | cut -f1)"
}

do_menuconfig() {
  [[ -f $KSRC/.config ]] || do_config
  use_toolchain linux
  kmake "Open the kernel's interactive configuration menu" menuconfig
  info "To keep your changes in git, save a minimal fragment, e.g.:"
  info "  diff <(sort build/src/linux-$KERNEL_VERSION/.config.old) <(sort build/src/linux-$KERNEL_VERSION/.config) | grep '^>' | cut -c3- > config/kernel/my.cfg"
}

do_clean() {
  section "Cleaning kernel build (the unpacked source is kept)"
  use_toolchain linux
  [[ -d $KSRC ]] && run_make "Remove all build output and .config" "$KSRC" mrproper
  run "Remove the installed overlay" rm -rf "$OVERLAY" "$DEPLOY_DIR"/kernel*.tar.gz
}

main() {
  local target=${1:-all}
  [[ $target == menuconfig ]] || start_log "kernel-$target"
  case $target in
    all)        do_config; do_build; do_install ;;
    config)     do_config ;;
    build)      do_build ;;
    install)    do_install ;;
    menuconfig) do_menuconfig ;;
    clean)      do_clean ;;
    *) die "unknown target '$target' (all|config|build|install|menuconfig|clean)" ;;
  esac
}

main "$@"
