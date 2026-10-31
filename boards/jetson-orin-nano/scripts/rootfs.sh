#!/usr/bin/env bash
# =============================================================================
#  scripts/rootfs.sh - assemble the root filesystem inside Linux_for_Tegra/
# =============================================================================
#
#  NVIDIA's recipe (Developer Guide, "Quick Start"), one command per line:
#
#    tar xf Jetson_Linux_….tbz2                          the driver package
#    sudo tar xpf Tegra_Linux_Sample-Root-Filesystem_….tbz2 -C Linux_for_Tegra/rootfs/
#    sudo ./apply_binaries.sh                            NVIDIA's userspace on top
#    sudo ./tools/l4t_create_default_user.sh …           a login, so no first-boot wizard
#
#  Why root: the rootfs holds files owned by root, device nodes and setuid
#  binaries; `tar -p` can only recreate those when run as root. This is the
#  one step of this board that needs sudo (the flash steps need it too).
#
#  Each sub-step leaves a stamp in build/work/ so a re-run skips what is done.
#  To redo the rootfs from scratch: ./build.sh clean (it removes build/work).
#
#  Usage: scripts/rootfs.sh        (normally called through ./build.sh rootfs)
# =============================================================================
# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
strict_mode
load_config

ROOTFS="$L4T_DIR/rootfs"

main() {
  start_log "rootfs"
  host_check
  need_cmd sudo tar lbzip2 qemu-aarch64-static
  section "Root filesystem (Ubuntu 22.04 userland + NVIDIA libraries)"

  ensure_bsp

  if [[ -f $WORK_DIR/.stamp-rootfs-tar ]]; then
    info "Sample root filesystem already unpacked"
  else
    fetch "$ROOTFS_URL" "$DL_DIR/$ROOTFS_FILE" "$ROOTFS_SHA256"
    explain "The sample rootfs is a bare Ubuntu 22.04 (jammy) arm64 userland. It" \
            "has no NVIDIA drivers or libraries yet and no user account."
    run "Unpack the sample rootfs as root, keeping owners and permissions (-p)" \
      sudo tar -xpf "$DL_DIR/$ROOTFS_FILE" -C "$ROOTFS/"
    [[ $DRY_RUN == 1 ]] || touch "$WORK_DIR/.stamp-rootfs-tar"
  fi

  run_cd "NVIDIA's scripts expect to run from the top of Linux_for_Tegra" "$L4T_DIR"

  if [[ -f $WORK_DIR/.stamp-apply-binaries ]]; then
    info "NVIDIA userspace already applied"
  else
    explain "apply_binaries.sh installs NVIDIA's L4T Debian packages (GPU, display," \
            "camera, multimedia, nvpmodel, bootloader updater, ...) into the rootfs" \
            "through a qemu-user chroot, unpacks the stock kernel modules and firmware," \
            "writes /boot/extlinux/extlinux.conf and builds the initrd (copied to" \
            "bootloader/l4t_initrd.img for the flash tool)."
    run "Install NVIDIA's userspace and the stock kernel into the rootfs" sudo ./apply_binaries.sh
    [[ $DRY_RUN == 1 ]] || touch "$WORK_DIR/.stamp-apply-binaries"
  fi

  if [[ -f $WORK_DIR/.stamp-default-user ]]; then
    info "Default user already created"
  else
    if [[ $ACCEPT_LICENSE != 1 && $DRY_RUN != 1 ]]; then
      die "Creating the default user accepts NVIDIA's Tegra Software License Agreement.
       Read it:  $L4T_DIR/Tegra_Software_License_Agreement-Tegra-Linux.txt
       then re-run with:  ./build.sh --accept-license rootfs"
    fi
    explain "Without a user account the first boot starts NVIDIA's 'oem-config'" \
            "wizard (on a monitor, or over the USB serial console ttyGS0). Creating" \
            "the account now skips that wizard. '$TARGET_PASSWORD' is a bench default:" \
            "change it (config/local.conf) for anything but a board on your desk."
    run "Create user '$TARGET_USER' and hostname '$TARGET_HOSTNAME' inside the rootfs" \
      sudo ./tools/l4t_create_default_user.sh -u "$TARGET_USER" -p "$TARGET_PASSWORD" -n "$TARGET_HOSTNAME" --accept-license
    [[ $DRY_RUN == 1 ]] || touch "$WORK_DIR/.stamp-default-user"
  fi

  [[ $DRY_RUN == 1 ]] || info "Root filesystem ready: $ROOTFS ($(sudo du -sh "$ROOTFS" | cut -f1))"
}

main "$@"
