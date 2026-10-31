# shellcheck shell=bash
# =============================================================================
#  scripts/lib/common.sh - helpers shared by every build step
# =============================================================================
#
#  This file is sourced (never executed). It provides:
#
#    * logging          : info / warn / die / section
#    * run              : print WHY + the exact command, then execute it
#                         (prints only, when DRY_RUN=1  ->  "explain mode")
#    * fetch            : download a file once and verify its sha256
#    * setup_toolchain  : make CROSS_COMPILE point at NVIDIA's reference gcc
#    * apply_patches    : apply patches/source/*.patch to the kernel sources
#    * host_check       : explain (and enforce) the x86-64 Linux host rule
#
#  Directory layout (everything generated lives under build/, git-ignored):
#
#    build/downloads/              NVIDIA archives (cached, sha256 verified)
#    build/toolchain/              unpacked NVIDIA reference cross compiler
#    build/work/Linux_for_Tegra/   THE working tree: BSP + rootfs + sources.
#                                  NVIDIA's flash tools run from here
#    build/deploy/                 FINAL ARTIFACTS: Image, dtbs, flash command
#    build/logs/                   one log file per step
#
#  Unlike the SD-card boards of this repository there is no sdcard.img: the
#  "image" is the Linux_for_Tegra tree plus the flash package that NVIDIA's
#  initrd-flash tool generates from it (see docs/06-flash-package.md).
# =============================================================================

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
# TOP_DIR is the repository root; it is computed from this file's location so
# the scripts work no matter which directory you call them from.
TOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PATCH_DIR="$TOP_DIR/patches"

# Derived from BUILD_DIR; re-run by load_config so that BUILD_DIR may be set
# in config/local.conf.
set_paths() {
  : "${BUILD_DIR:=$TOP_DIR/build}"
  DL_DIR="$BUILD_DIR/downloads"
  WORK_DIR="$BUILD_DIR/work"
  # NVIDIA's archives all unpack into a directory called Linux_for_Tegra
  L4T_DIR="$WORK_DIR/Linux_for_Tegra"
  L4T_SRC="$L4T_DIR/source"
  DEPLOY_DIR="$BUILD_DIR/deploy"
  LOG_DIR="$BUILD_DIR/logs"
  TOOLCHAIN_DIR="$BUILD_DIR/toolchain"
}
set_paths

# -----------------------------------------------------------------------------
# Global switches (set by build.sh from the command line, or by environment)
# -----------------------------------------------------------------------------
: "${DRY_RUN:=0}"     # 1 = print every command with its explanation, run nothing
: "${VERBOSE:=0}"     # 1 = pass V=1 to make so every compiler call is shown
: "${UPDATE:=0}"      # 1 = throw away the extracted sources and unpack + patch them again
: "${JOBS:=$(nproc 2>/dev/null || echo 4)}" # parallel make jobs
: "${ASSUME_YES:=0}"  # 1 = do not ask for confirmation (DANGEROUS with flash)
: "${ACCEPT_LICENSE:=0}" # 1 = you have read and accept NVIDIA's Tegra Software License Agreement

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
# Colours only when writing to a terminal, so log files stay clean.
if [[ -t 1 ]]; then
  C_RESET=$'\e[0m'; C_BOLD=$'\e[1m'; C_DIM=$'\e[2m'
  C_RED=$'\e[31m'; C_GREEN=$'\e[32m'; C_YELLOW=$'\e[33m'; C_BLUE=$'\e[34m'; C_CYAN=$'\e[36m'
else
  C_RESET=; C_BOLD=; C_DIM=; C_RED=; C_GREEN=; C_YELLOW=; C_BLUE=; C_CYAN=
fi

ts()      { date '+%H:%M:%S'; }
info()    { printf '%s[%s]%s %s\n' "$C_GREEN" "$(ts)" "$C_RESET" "$*"; }
warn()    { printf '%s[%s] WARNING:%s %s\n' "$C_YELLOW" "$(ts)" "$C_RESET" "$*" >&2; }
die()     { printf '%s[%s] ERROR:%s %s\n' "$C_RED" "$(ts)" "$C_RESET" "$*" >&2; exit 1; }
section() { printf '\n%s==== %s ====%s\n' "$C_BOLD$C_BLUE" "$*" "$C_RESET"; }

# run "<why this command exists>" cmd arg1 arg2 ...
#
# Prints the explanation and the exact, copy-pasteable command, then runs it.
# With DRY_RUN=1 nothing is executed, so `./build.sh <step> --dry-run` turns
# into a step-by-step manual of how to do the build by hand.
run() {
  local why=$1; shift
  printf '%s  # %s%s\n' "$C_DIM" "$why" "$C_RESET"
  printf '%s  $ %s%s\n' "$C_CYAN" "$(short_paths "$(quote_cmd "$@")")" "$C_RESET"
  [[ $DRY_RUN == 1 ]] && return 0
  "$@"
}

# run_sh "<why>" '<shell command line with pipes/redirections>'
# For commands that need a pipe or redirection: the string is shown verbatim
# (readable!) and executed with bash -c.
run_sh() {
  local why=$1 cmd=$2
  printf '%s  # %s%s\n' "$C_DIM" "$why" "$C_RESET"
  printf '%s  $ %s%s\n' "$C_CYAN" "$(short_paths "$cmd")" "$C_RESET"
  [[ $DRY_RUN == 1 ]] && return 0
  bash -o pipefail -c "$cmd"
}

# Same as run, but for "cd": it changes the directory of the calling script
# (also in dry-run, when the directory exists, so later steps print sensibly).
run_cd() {
  local why=$1 dir=$2
  printf '%s  # %s%s\n' "$C_DIM" "$why" "$C_RESET"
  printf '%s  $ cd %s%s\n' "$C_CYAN" "$(short_paths "$(printf '%q' "$dir")")" "$C_RESET"
  if [[ $DRY_RUN == 1 ]]; then
    cd "$dir" 2>/dev/null || true
  else
    cd "$dir" || die "cannot cd to $dir"
  fi
}

# Display only: write the build directory as $B so commands stay short and
# can still be copy-pasted after `export B=<build dir>` (printed at start).
short_paths() { local s=$1; printf '%s' "${s//"$BUILD_DIR"/\$B}"; }

# Render an argv array as a shell-quoted command line (for display only).
# Prefers readable 'single quotes'; for --option=value only the value is quoted.
quote_cmd() {
  local out='' a
  for a in "$@"; do
    if [[ $a =~ ^[A-Za-z0-9_./:=+,@%-]+$ ]]; then out+="$a "
    elif [[ $a =~ ^(--?[A-Za-z0-9_-]+=)(.*)$ ]]; then out+="${BASH_REMATCH[1]}$(quote_val "${BASH_REMATCH[2]}") "
    else out+="$(quote_val "$a") "; fi
  done
  printf '%s' "${out% }"
}
quote_val() {
  local v=$1
  if [[ $v =~ ^[A-Za-z0-9_./:=+,@%-]*$ && -n $v ]]; then printf '%s' "$v"
  elif [[ $v != *"'"* ]]; then printf "'%s'" "$v"
  else v=${v//\\/\\\\}; v=${v//\"/\\\"}; v=${v//\$/\\\$}; v=${v//\`/\\\`}; printf '"%s"' "$v"; fi
}

# Explain a concept in a few lines, before a group of commands.
explain() { printf '%s%s%s\n' "$C_DIM" "$*" "$C_RESET" | sed 's/^/  /'; }

# -----------------------------------------------------------------------------
# Error handling: print the failing command and line, plus where the log is.
# -----------------------------------------------------------------------------
on_error() {
  local rc=$? line=$1 cmd=$2 i
  printf '\n%s[%s] FAILED (exit %s)%s\n' "$C_RED" "$(ts)" "$rc" "$C_RESET" >&2
  if [[ $cmd == '"$@"' || $cmd == 'bash -o pipefail -c "$cmd"' ]]; then
    printf '    command: the last "$ ..." line printed above\n' >&2
  else
    printf '    command: %s\n' "$cmd" >&2
  fi
  # Call stack, innermost first, e.g. "run (common.sh:83) <- do_atf (uboot.sh:97)"
  printf '    where:   %s:%s' "${BASH_SOURCE[1]##*/}" "$line" >&2
  for ((i = 1; i < ${#FUNCNAME[@]} - 1; i++)); do
    printf ' <- %s (%s:%s)' "${FUNCNAME[i]}" "${BASH_SOURCE[i+1]##*/}" "${BASH_LINENO[i]}" >&2
  done
  printf '\n' >&2
  [[ -n ${CURRENT_LOG:-} ]] && printf '    log:     %s\n' "$CURRENT_LOG" >&2
  printf '    help:    docs/09-troubleshooting.md\n' >&2
  exit "$rc"
}

# Call at the top of every step script.
#   -E  : ERR trap is inherited by functions
#   -e  : stop at the first failing command
#   -u  : using an unset variable is an error (catches typos)
#   -o pipefail : a pipeline fails if ANY command in it fails, not just the last
strict_mode() {
  set -Eeuo pipefail
  trap 'on_error $LINENO "$BASH_COMMAND"' ERR
}

# Send all further output of the current script to the terminal AND a log file.
start_log() {
  local name=$1
  export B="$BUILD_DIR"
  explain "In the commands below \$B = $BUILD_DIR"
  [[ $DRY_RUN == 1 ]] && return 0
  mkdir -p "$LOG_DIR"
  CURRENT_LOG="$LOG_DIR/$name-$(date +%Y%m%d-%H%M%S).log"
  ln -sfn "$(basename "$CURRENT_LOG")" "$LOG_DIR/$name.log"
  # The terminal keeps its colours; the copy in the log file has them stripped.
  exec > >(tee >(sed -u 's/\x1b\[[0-9;]*m//g' >>"$CURRENT_LOG")) 2>&1
  info "Logging to $CURRENT_LOG"
}

# -----------------------------------------------------------------------------
# Small checks
# -----------------------------------------------------------------------------
need_cmd() {
  local missing=() c
  for c in "$@"; do command -v "$c" >/dev/null 2>&1 || missing+=("$c"); done
  ((${#missing[@]} == 0)) && return 0
  if [[ $DRY_RUN == 1 ]]; then warn "missing host tool(s): ${missing[*]} (ignored in dry-run)"; return 0; fi
  die "missing host tool(s): ${missing[*]}  ->  run: ./build.sh deps"
}

need_file() {
  [[ $DRY_RUN == 1 ]] && return 0
  local f
  for f in "$@"; do [[ -e $f ]] || die "required file not found: $f"; done
}

confirm() {
  [[ $ASSUME_YES == 1 ]] && return 0
  local reply
  read -r -p "$1 [y/N] " reply
  [[ $reply =~ ^[Yy]([Ee][Ss])?$ ]]
}

# Warn early instead of failing an hour into the build.
check_disk_space() {
  local need_gb=$1 free_gb
  mkdir -p "$BUILD_DIR"
  free_gb=$(df -P -BG "$BUILD_DIR" | awk 'NR==2 {gsub("G","",$4); print $4}')
  if (( free_gb < need_gb )); then
    warn "Only ${free_gb} GB free in $BUILD_DIR, the build needs about ${need_gb} GB."
    confirm "Continue anyway?" || die "not enough disk space (set BUILD_DIR to another disk in config/local.conf)"
  fi
}

# Human-readable size of a file.
hsize() { [[ -e $1 ]] || { echo "?"; return 0; }; du -h "$1" | cut -f1; }

# -----------------------------------------------------------------------------
# apply_patches
#
# Applies patches/source/*.patch, in name order, exactly once, to the extracted
# Jetson Linux sources (Linux_for_Tegra/source). Paths inside a patch are
# relative to that directory (patch -p1), so one patch can touch the kernel
# (kernel/kernel-jammy-src/...), the NVIDIA out-of-tree modules (nvidia-oot/...)
# and the device trees (hardware/nvidia/...) together.
# A marker file inside the source tree remembers what was applied.
# -----------------------------------------------------------------------------
apply_patches() {
  local p stamp="$L4T_SRC/.applied-patches"
  compgen -G "$PATCH_DIR/source/*.patch" >/dev/null || return 0
  [[ $DRY_RUN == 1 ]] || touch "$stamp"
  for p in "$PATCH_DIR"/source/*.patch; do
    if [[ $DRY_RUN != 1 ]] && grep -qxF "$(basename "$p")" "$stamp"; then
      info "patch $(basename "$p") already applied"
      continue
    fi
    run "Apply local patch $(basename "$p") to the Jetson Linux sources" \
      patch -d "$L4T_SRC" -p1 --no-backup-if-mismatch -i "$p"
    [[ $DRY_RUN == 1 ]] || basename "$p" >>"$stamp"
  done
}

# -----------------------------------------------------------------------------
# fetch <url> <dest-file> [sha256]
# Download once (resumable) and verify the checksum when one is given.
# -----------------------------------------------------------------------------
fetch() {
  local url=$1 dest=$2 sha=${3:-}
  mkdir -p "$(dirname "$dest")"
  if [[ ! -s $dest ]]; then
    run "Download $(basename "$dest")" \
      wget --no-verbose --show-progress --continue -O "$dest.part" "$url"
    [[ $DRY_RUN == 1 ]] || mv "$dest.part" "$dest"
  else
    info "Already downloaded: $dest"
  fi
  if [[ -n $sha ]]; then
    run_sh "Verify the download against the known sha256 (protects against corrupt/tampered files)" \
      "echo '$sha  $dest' | sha256sum --check --quiet"
  fi
}

# -----------------------------------------------------------------------------
# host_check
#
# NVIDIA's flashing tools and its reference cross compiler only exist for
# x86-64 Linux ("Ubuntu 20.04 or 22.04" in NVIDIA's Quick Start). In explain
# mode (--dry-run) we only warn, so the recipe stays readable anywhere.
# -----------------------------------------------------------------------------
host_check() {
  local arch os problems=()
  arch=$(uname -m); os=$(uname -s)
  [[ $os == Linux ]] || problems+=("this is $os, not Linux")
  [[ $arch == x86_64 ]] || problems+=("this machine is $arch, not x86_64")
  ((${#problems[@]} == 0)) && return 0
  if [[ $DRY_RUN == 1 ]]; then
    warn "host check: ${problems[*]}. Fine for reading the recipe; a real build needs an x86-64 Linux PC"
    return 0
  fi
  die "NVIDIA's Jetson Linux tools run only on an x86-64 Linux PC (${problems[*]}).
       Use a PC, a VM or a cloud machine with Ubuntu 22.04 (or 20.04) x86-64.
       You can still read every step: ./build.sh --dry-run all"
}

# -----------------------------------------------------------------------------
# setup_toolchain
# Exports ARCH and CROSS_COMPILE. NVIDIA names the reference compiler in its
# Developer Guide ("Jetson Linux Toolchain"): Bootlin's aarch64--glibc--stable-
# 2022.08-1, whose tools are called aarch64-buildroot-linux-gnu-*.
# -----------------------------------------------------------------------------
setup_toolchain() {
  export ARCH=arm64
  local dir="$TOOLCHAIN_DIR/$TOOLCHAIN_TOP"
  CROSS_COMPILE="$dir/bin/aarch64-buildroot-linux-gnu-"
  export CROSS_COMPILE
  # Once per script run, so the explain-mode output does not repeat itself.
  [[ ${TOOLCHAIN_READY:-0} == 1 ]] && return 0
  TOOLCHAIN_READY=1
  if [[ ! -x $dir/bin/aarch64-buildroot-linux-gnu-gcc ]]; then
    section "Installing NVIDIA's reference toolchain (one-time)"
    fetch "$TOOLCHAIN_URL" "$DL_DIR/$TOOLCHAIN_FILE" "$TOOLCHAIN_SHA256"
    run "Create the toolchain directory" mkdir -p "$TOOLCHAIN_DIR"
    run "Unpack the toolchain into build/toolchain" tar -xjf "$DL_DIR/$TOOLCHAIN_FILE" -C "$TOOLCHAIN_DIR"
  fi
  explain "CROSS_COMPILE=$(short_paths "$CROSS_COMPILE")"
  if [[ $DRY_RUN != 1 ]]; then
    info "Cross compiler: $("${CROSS_COMPILE}gcc" --version | head -n1)"
  fi
}

# -----------------------------------------------------------------------------
# The Linux_for_Tegra tree
# -----------------------------------------------------------------------------

# Unpack NVIDIA's driver package (flash tools, bootloader binaries, prebuilt
# kernel) once. Used by the rootfs and kernel steps, so either can go first.
ensure_bsp() {
  local stamp="$WORK_DIR/.stamp-bsp"
  # Once per script run, so the explain-mode output does not repeat itself.
  [[ ${BSP_READY:-0} == 1 ]] && return 0
  BSP_READY=1
  if [[ -f $stamp ]]; then
    info "Driver package already unpacked: $L4T_DIR"
    return 0
  fi
  section "Unpacking NVIDIA's driver package (Linux_for_Tegra)"
  fetch "$BSP_URL" "$DL_DIR/$BSP_FILE" "$BSP_SHA256"
  run "Create the working directory" mkdir -p "$WORK_DIR"
  explain "The archive contains one directory, Linux_for_Tegra/. It holds flash.sh," \
          "the initrd flashing tool, every boot firmware binary and the prebuilt" \
          "kernel. Unpacking it as your own user is fine: root is only needed" \
          "for the root filesystem, whose files must be owned by root."
  run "Unpack the driver package" tar -xjf "$DL_DIR/$BSP_FILE" -C "$WORK_DIR"
  [[ $DRY_RUN == 1 ]] || touch "$stamp"
}

# -----------------------------------------------------------------------------
# Pieces of the l4t_initrd_flash.sh command line, shared by image.sh/flash.sh
# (NVIDIA Quick Start, "Jetson Orin Nano Developer Kit (NVMe / USB / SD card)")
# -----------------------------------------------------------------------------
# The device name the TARGET sees for the chosen root device.
external_device() {
  case $ROOT_DEVICE in
    nvme) echo nvme0n1p1 ;;
    sd)   echo mmcblk0p1 ;;
    usb)  echo sda1 ;;
    *) die "ROOT_DEVICE='$ROOT_DEVICE' is not valid (use nvme, sd or usb)" ;;
  esac
}

# UEFI decides which device it tries first. NVIDIA's README_initrd_flash.txt
# documents ADDITIONAL_DTB_OVERLAY_OPT with BootOrderNvme.dtbo / BootOrderUsb.dtbo;
# BootOrderSD.dtbo sits next to them in kernel/dtb.
boot_order_overlay() {
  case ${BOOT_ORDER_OVERLAY:-auto} in
    auto) case $ROOT_DEVICE in
            nvme) echo BootOrderNvme.dtbo ;;
            sd)   echo BootOrderSD.dtbo ;;
            usb)  echo BootOrderUsb.dtbo ;;
          esac ;;
    none) ;;
    *)    echo "$BOOT_ORDER_OVERLAY" ;;
  esac
}

# Fills INITRD_ENV (VAR=value words for `sudo env`) and INITRD_ARGS.
initrd_flash_args() {
  local ov; ov=$(boot_order_overlay)
  INITRD_ENV=()
  [[ -n $ov ]] && INITRD_ENV+=("ADDITIONAL_DTB_OVERLAY_OPT=$ov")
  INITRD_ARGS=(--external-device "$(external_device)" -c "$EXT_LAYOUT" -p "-c $QSPI_LAYOUT" --network "$FLASH_NETWORK")
  [[ -n $APP_SIZE ]] && INITRD_ARGS+=(-S "$APP_SIZE")
  return 0
}

# Print the lsusb lines of Jetson modules that are in Force Recovery Mode.
recovery_devices() {
  command -v lsusb >/dev/null || return 0
  local id
  for id in $RECOVERY_USB_IDS; do lsusb -d "$id" || true; done
}

# Load configuration: optional user overrides first, then the defaults.
load_config() {
  # shellcheck source=/dev/null
  [[ -f $TOP_DIR/config/local.conf ]] && source "$TOP_DIR/config/local.conf"
  # shellcheck source=../../config/jetson-orin-nano.conf
  source "$TOP_DIR/config/jetson-orin-nano.conf"
  set_paths
}
