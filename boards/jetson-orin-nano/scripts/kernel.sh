#!/usr/bin/env bash
# =============================================================================
#  scripts/kernel.sh - build the Jetson kernel, NVIDIA modules and device trees
# =============================================================================
#
#  This is NVIDIA's "Kernel Customization" procedure (Developer Guide), as a
#  script. Four things get built from the public sources, and they land in
#  three different places:
#
#    what                          built by                     installed to
#    ----------------------------  ---------------------------  --------------------
#    Image (Linux 5.15.148-tegra)  make -C kernel               kernel/Image
#    in-tree modules               make -C kernel               rootfs/lib/modules/…
#    NVIDIA out-of-tree modules    make modules  (nvidia-oot,   rootfs/lib/modules/…
#      (GPU, display, camera, …)     hwpm, nvgpu, nvdisplay)      /updates
#    device trees (*.dtb)          make dtbs  (kernel-devicetree)  kernel/dtb/
#
#  followed by regenerating the initrd (tools/l4t_update_initrd.sh), because it
#  contains modules. Nothing is flashed here: the next step, image/flash,
#  picks everything up from Linux_for_Tegra/.
#
#  Where your own changes go (all optional, all documented in docs/08):
#    config/kernel/*.cfg     kernel config fragments, merged after defconfig
#    patches/source/*.patch  patches (patch -p1 from Linux_for_Tegra/source)
#
#  Usage: scripts/kernel.sh [all|extract|config|build|install|menuconfig|clean]
#         (normally called through ./build.sh kernel)
# =============================================================================
# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
strict_mode
load_config

KSRC="$L4T_SRC/kernel/$KERNEL_SRC_DIR"
FRAGMENT_DIR="$TOP_DIR/config/kernel"
ROOTFS="$L4T_DIR/rootfs"

# Every kernel make call gets the same LOCALVERSION that NVIDIA's own
# source/kernel/Makefile passes, otherwise the Image's version string and the
# /lib/modules/<version> directory would disagree and modules would not load.
kmake() { local why=$1; shift; run "$why" make -C "$KSRC" -j"$JOBS" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" LOCALVERSION="$KERNEL_LOCALVERSION" "$@"; }

# NVIDIA's top-level source/Makefile builds the out-of-tree parts. It reads the
# kernel tree from KERNEL_HEADERS and the compiler from CROSS_COMPILE.
omake() { local why=$1; shift; run "$why" env KERNEL_HEADERS="$KSRC" NPROC="$JOBS" make -C "$L4T_SRC" "$@"; }

# -----------------------------------------------------------------------------
do_extract() {
  section "Jetson Linux sources (R$L4T_RELEASE)"
  ensure_bsp
  if [[ -f $L4T_SRC/.extracted && $UPDATE != 1 ]]; then
    info "Sources already unpacked in $L4T_SRC (pass --update to unpack them again)"
    apply_patches    # idempotent: only patches that were not applied yet run
    return 0
  fi
  fetch "$SOURCES_URL" "$DL_DIR/$SOURCES_FILE" "$SOURCES_SHA256"
  if [[ $UPDATE == 1 && -d $L4T_SRC/kernel ]]; then
    run "Throw away the previously extracted source trees" \
      rm -rf "$L4T_SRC/kernel" "$L4T_SRC/kernel-devicetree" "$L4T_SRC/nvidia-oot" "$L4T_SRC/hwpm" \
             "$L4T_SRC/nvgpu" "$L4T_SRC/nvdisplay" "$L4T_SRC/nvethernetrm" "$L4T_SRC/hardware" \
             "$L4T_SRC/.extracted" "$L4T_SRC/.applied-patches"
  fi
  explain "public_sources.tbz2 is a bundle of source archives. It unpacks into" \
          "Linux_for_Tegra/source/, next to the files already there."
  run "Unpack NVIDIA's public sources into the Linux_for_Tegra tree" tar -xjf "$DL_DIR/$SOURCES_FILE" -C "$WORK_DIR"
  explain "Three of those archives together are the kernel build: the kernel itself" \
          "(into kernel/$KERNEL_SRC_DIR), and the NVIDIA modules, device trees and display driver" \
          "(into the current directory: nvidia-oot, hwpm, nvgpu, nvdisplay, hardware, kernel-devicetree)."
  run_cd "Work inside Linux_for_Tegra/source" "$L4T_SRC"
  run "Unpack the kernel" tar -xf kernel_src.tbz2
  run "Unpack NVIDIA's out-of-tree modules and device trees" tar -xf kernel_oot_modules_src.tbz2
  run "Unpack NVIDIA's display driver" tar -xf nvidia_kernel_display_driver_source.tbz2
  apply_patches
  [[ $DRY_RUN == 1 ]] || touch "$L4T_SRC/.extracted"
}

# True when a config fragment was added or edited after the .config was made.
fragments_changed() {
  local f
  for f in "$FRAGMENT_DIR"/*.cfg; do
    [[ -e $f && $f -nt $KSRC/.config ]] && return 0
  done
  return 1
}

# -----------------------------------------------------------------------------
do_config() {
  setup_toolchain
  do_extract
  section "Kernel configuration ($KERNEL_DEFCONFIG)"
  if [[ -f $KSRC/.config && ${FORCE_CONFIG:-0} != 1 ]] && ! fragments_changed; then
    info "Keeping existing .config (it is newer than every fragment in config/kernel/; FORCE_CONFIG=1 regenerates it)"
    return 0
  fi
  explain "NVIDIA's source/kernel/Makefile runs 'defconfig', then Image, dtbs and" \
          "modules in one go. We run the same make commands one by one so that your" \
          "config fragments can be merged between defconfig and the compile."
  kmake "Create .config from arch/arm64/configs/$KERNEL_DEFCONFIG" "$KERNEL_DEFCONFIG"
  if compgen -G "$FRAGMENT_DIR/*.cfg" >/dev/null; then
    run "Merge config fragments from config/kernel/ on top of the defconfig" \
      env ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" \
      "$KSRC/scripts/kconfig/merge_config.sh" -m -O "$KSRC" "$KSRC/.config" "$FRAGMENT_DIR"/*.cfg
    kmake "Resolve dependencies of the merged options (new symbols get defaults)" olddefconfig
  fi
}

# -----------------------------------------------------------------------------
do_build() {
  [[ -f $KSRC/.config ]] || do_config
  setup_toolchain
  section "Compiling the kernel and NVIDIA's modules with $JOBS jobs"
  explain "First build takes a while (the kernel, then NVIDIA's GPU/display/camera" \
          "modules). Rebuilds only recompile what changed."
  kmake "Compile the kernel image" Image
  kmake "Compile the kernel's own device trees" dtbs
  kmake "Compile the in-tree modules" modules
  # nvidia-oot & friends are built against the kernel tree we just compiled.
  omake "Compile NVIDIA's out-of-tree modules (nvidia-oot, hwpm, nvgpu, nvdisplay)" modules CROSS_COMPILE="$CROSS_COMPILE"
  omake "Compile NVIDIA's device trees (the Orin Nano ones are in here)" dtbs CROSS_COMPILE="$CROSS_COMPILE"
}

# -----------------------------------------------------------------------------
do_install() {
  setup_toolchain
  section "Installing into Linux_for_Tegra"
  need_cmd sudo
  local release_note="make -C source/kernel install"
  explain "'$release_note' (NVIDIA) copies the Image to <rootfs>/boot and runs" \
          "modules_install into <rootfs>/lib/modules/<version>. The rootfs is owned by root, so sudo."
  run "Install the kernel Image and in-tree modules into the rootfs" \
    sudo env INSTALL_MOD_PATH="$ROOTFS/" KERNEL_SRC_DIR="$KERNEL_SRC_DIR" make -C "$L4T_SRC/kernel" install
  explain "INSTALL_MOD_DIR=updates puts NVIDIA's modules in lib/modules/<version>/updates/," \
          "the same place the stock kernel_oot_modules package uses (and what NVIDIA's nvbuild.sh does)."
  run "Install NVIDIA's out-of-tree modules into the rootfs" \
    sudo env INSTALL_MOD_PATH="$ROOTFS/" INSTALL_MOD_DIR=updates KERNEL_HEADERS="$KSRC" CROSS_COMPILE="$CROSS_COMPILE" make -C "$L4T_SRC" modules_install
  explain "The flash tool takes the kernel for the 'kernel' partition from" \
          "Linux_for_Tegra/kernel/Image and the device tree from kernel/dtb/, NOT from the rootfs."
  run "Use the new Image for the kernel partition" cp "$KSRC/arch/arm64/boot/Image" "$L4T_DIR/kernel/Image"
  run_sh "Use the new device trees for the kernel-dtb partition" \
    "cp $L4T_SRC/kernel-devicetree/generic-dts/dtbs/* $L4T_DIR/kernel/dtb/"
  run_cd "Regenerate the initrd from the rootfs, because it contains modules" "$L4T_DIR"
  run "Rebuild the initrd (runs nv-update-initrd in the rootfs through qemu)" sudo ./tools/l4t_update_initrd.sh
  [[ $DRY_RUN == 1 ]] || info "Kernel $(strings "$L4T_DIR/kernel/Image" 2>/dev/null | grep -m1 -E '^Linux version' | cut -c1-60) installed"
}

do_menuconfig() {
  [[ -f $KSRC/.config ]] || do_config
  setup_toolchain
  kmake "Open the kernel's interactive configuration menu" menuconfig
  info "To keep your changes in git, save a minimal fragment, e.g.:"
  info "  cd $KSRC && cp .config /tmp/after && make ARCH=arm64 $KERNEL_DEFCONFIG && scripts/diffconfig .config /tmp/after"
  info "and put the CONFIG_ lines you want into config/kernel/my.cfg"
}

do_clean() {
  section "Cleaning the kernel build (sources are kept)"
  if [[ -d $KSRC ]]; then
    setup_toolchain
    kmake "Remove all kernel build output and .config" mrproper
    omake "Remove NVIDIA module and device tree build output" clean CROSS_COMPILE="$CROSS_COMPILE"
  else
    info "No kernel source tree yet"
  fi
}

main() {
  local target=${1:-all}
  [[ $target == menuconfig ]] || start_log "kernel-$target"
  host_check
  case $target in
    all)        do_config; do_build; do_install ;;
    extract)    do_extract ;;
    config)     do_config ;;
    build)      do_build ;;
    install)    do_install ;;
    menuconfig) do_menuconfig ;;
    clean)      do_clean ;;
    *) die "unknown target '$target' (all|extract|config|build|install|menuconfig|clean)" ;;
  esac
}

main "$@"
