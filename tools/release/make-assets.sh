#!/usr/bin/env bash
# =============================================================================
#  tools/release/make-assets.sh - turn a finished board build into release assets
# =============================================================================
#
#  Usage:  tools/release/make-assets.sh <board> <variant> <outdir>
#
#  Run it AFTER the build commands listed for that variant in images.json (for
#  example `./build.sh -r alpine all` inside the board directory). It reads
#  <board dir>/build/deploy/ and writes into <outdir>:
#
#    <name>.img.xz          the image, compressed (xz -T1 -6, see below)
#    <name>.img.bmap        block map for bmaptool, copied unchanged
#    <asset>.sha256         one line per asset, in `sha256sum` format
#    manifest.json          board, variant, tag, commit, build date, pinned sources,
#                           tool versions, sizes, raw + compressed sha256, verified flag
#
#  Environment (all optional):
#    RELEASE_TAG         version label for the manifest (default: "untagged")
#    SOURCE_DATE_EPOCH   build date as Unix seconds (default: the commit time of HEAD)
#    DEPLOY_DIR          where the build left its files (default <board dir>/build/deploy)
#    GIT_COMMIT          commit to record (default: git rev-parse HEAD)
#    INFO_FILE           use this text instead of running `./build.sh info` (tests)
#    CROSS_COMPILE       Jetson kernel bundle: prefix of NVIDIA's compiler (default: found under build/toolchain)
#
#  Why `xz -T1 -6`: the man page of xz states that "the single-threaded and
#  multi-threaded compressors produce different output" and that the output may
#  differ between xz versions. A fixed thread count removes one variable, so the
#  same input and the same xz version always give the same bytes; reading the
#  image from stdin (not by name) keeps the file name and mtime out of the .xz
#  header. Level 6 is xz's default, "usually a good choice for distributing
#  files" that must be decompressed on machines with little memory (about 9 MiB
#  for the decoder), unlike -9 (65 MiB). The price of -T1 is time, not size.
# =============================================================================
set -Eeuo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=$(cd "$here/../.." && pwd)

die() { echo "make-assets: $*" >&2; exit 1; }
info() { echo "make-assets: $*" >&2; }

[[ $# -eq 3 ]] || { sed -n '5,8p' "$0" | sed 's/^#  //' >&2; exit 2; }
board=$1 variant=$2 outdir=$3

sha256() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
fsize() { wc -c <"$1" | tr -d ' '; }

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

python3 "$here/matrix.py" --entry "$board" "$variant" >"$work/entry.json" || die "unknown board/variant"
entry_get() { python3 -c 'import json,sys; v=json.load(open(sys.argv[1])).get(sys.argv[2], ""); print(v if not isinstance(v, bool) else str(v).lower())' "$work/entry.json" "$1"; }

board_dir="$root/$(entry_get dir)"
[[ -d $board_dir ]] || die "board directory $board_dir does not exist"
deploy=${DEPLOY_DIR:-$board_dir/build/deploy}
[[ -d $deploy ]] || die "$deploy does not exist: run the build first (see images.json: build)"
kind_stage=$(entry_get stage)

commit=${GIT_COMMIT:-$(git -C "$root" rev-parse HEAD 2>/dev/null || echo unknown)}
sde=${SOURCE_DATE_EPOCH:-$(git -C "$root" log -1 --format=%ct 2>/dev/null || echo 0)}
tag=${RELEASE_TAG:-untagged}
export SOURCE_DATE_EPOCH=$sde
export TZ=UTC LC_ALL=C

mkdir -p "$outdir"
outdir=$(cd "$outdir" && pwd)
find "$outdir" -mindepth 1 -maxdepth 1 \( -name 'manifest.json' -o -name '*.sha256' \) -delete

# --- bundle staging ----------------------------------------------------------
# A "stage" builds one bundle file from several build outputs. The result path is left in $bundle_file.
bundle_file=""

deterministic_tar_xz() {  # <dir> <output.tar.xz> : sorted names, fixed owner, fixed mtime
  local dir=$1 out=$2
  tar --sort=name --owner=0 --group=0 --numeric-owner --format=gnu --mtime="@$sde" \
    -C "$dir" -cf - . | xz -T1 -6 -c >"$out"
}

stage_jetson_kernel() {
  # Reproduces the products of scripts/kernel.sh (build) without sudo and without the root filesystem:
  # Image, device trees and modules are taken from the build tree; nothing from NVIDIA's driver package
  # (Linux_for_Tegra/rootfs, tools, bootloader) is copied.
  local l4t_src="$board_dir/build/work/Linux_for_Tegra/source"
  local ksrc="$l4t_src/kernel/${KERNEL_SRC_DIR:-kernel-jammy-src}"
  local localversion=${KERNEL_LOCALVERSION:--tegra}
  local stage="$work/kernel-bundle"
  [[ -f $ksrc/arch/arm64/boot/Image ]] || die "no kernel Image at $ksrc/arch/arm64/boot/Image: run './build.sh kernel build' first"
  mkdir -p "$stage/dtb" "$stage/modules"
  cp "$ksrc/arch/arm64/boot/Image" "$stage/Image"
  local dtbdir="$l4t_src/kernel-devicetree/generic-dts/dtbs"
  compgen -G "$dtbdir/*.dtb" >/dev/null || die "no device trees in $dtbdir"
  cp "$dtbdir"/*.dtb "$stage/dtb/"
  local cc=${CROSS_COMPILE:-}
  if [[ -z $cc ]]; then
    cc=$(compgen -G "$board_dir/build/toolchain/*/bin/aarch64-buildroot-linux-gnu-gcc" | head -n1 || true)
    cc=${cc%gcc}
  fi
  make -C "$ksrc" ARCH=arm64 ${cc:+CROSS_COMPILE="$cc"} LOCALVERSION="$localversion" \
    INSTALL_MOD_PATH="$stage/modules" INSTALL_MOD_STRIP=1 modules_install >&2
  env KERNEL_HEADERS="$ksrc" ${cc:+CROSS_COMPILE="$cc"} INSTALL_MOD_PATH="$stage/modules" \
    INSTALL_MOD_DIR=updates INSTALL_MOD_STRIP=1 make -C "$l4t_src" modules_install >&2
  # the build/ and source/ links point at absolute paths of the build machine
  find "$stage/modules" -maxdepth 4 -type l \( -name build -o -name source \) -delete
  local rel
  rel=$(strings "$stage/Image" | grep -m1 -E '^Linux version' | cut -c1-120 || true)
  printf '%s\n' "$rel" >"$stage/KERNEL_VERSION.txt"
  cat >"$stage/README.txt" <<README
Jetson Orin Nano kernel bundle
==============================

Contents: Image (arm64 kernel), dtb/ (device trees), modules/lib/modules/<version>/ (in-tree and NVIDIA
out-of-tree modules, stripped). Built from NVIDIA's public sources by boards/jetson-orin-nano.

NOT included: NVIDIA's Jetson Linux driver package, flash tools, bootloader firmware and the sample root
filesystem. NVIDIA's licence limits redistribution (see docs/image-licences.md). Download them yourself:

    cd boards/jetson-orin-nano && ./build.sh --accept-license fetch bsp && ./build.sh --accept-license rootfs

Applying the bundle to a Linux_for_Tegra tree that already has its root filesystem (this repeats what
scripts/kernel.sh does in its "install" step; run it on the x86-64 Ubuntu flash host):

    L4T=boards/jetson-orin-nano/build/work/Linux_for_Tegra
    sudo cp -a modules/lib/modules/* "\$L4T/rootfs/lib/modules/"
    sudo cp Image "\$L4T/rootfs/boot/Image"
    cp Image "\$L4T/kernel/Image"
    cp dtb/*.dtb "\$L4T/kernel/dtb/"
    (cd "\$L4T" && sudo ./tools/l4t_update_initrd.sh)

then flash as usual (./build.sh image && ./build.sh flash). Verify the kernel string first: KERNEL_VERSION.txt.
README
  find "$stage" -exec touch -h -d "@$sde" {} + 2>/dev/null || true
  bundle_file="$work/bundle.out"
  deterministic_tar_xz "$stage" "$bundle_file"
}

stage_uuu_bundle() {
  local stage="$work/uuu-bundle" pat f
  mkdir -p "$stage"
  while IFS= read -r pat; do
    local n=0
    for f in "$deploy"/$pat; do
      [[ -e $f ]] || continue
      cp -RL "$f" "$stage/"
      n=$((n + 1))
    done
    [[ $n -gt 0 ]] || info "warning: bundle pattern '$pat' matched nothing in $deploy"
  done < <(python3 -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1])).get("bundle_files", [])))' "$work/entry.json")
  [[ -n $(ls -A "$stage") ]] || die "uuu bundle is empty: fix bundle_files in images.json"
  cat >"$stage/README.txt" <<'README'
uuu bundle: flash the on-module eMMC over USB with NXP's uuu (Universal Update Utility).
Get uuu for your PC from https://github.com/nxp-imx/mfgtools/releases . Put the board in serial download
mode (boot switch as in the board's README), connect the USB OTG port, then run the .uuu script
in this directory with uuu. Full steps: docs/downloads.md ("uuu") in the repository.
README
  find "$stage" -exec touch -h -d "@$sde" {} + 2>/dev/null || true
  command -v zip >/dev/null || die "zip is required for the uuu bundle"
  bundle_file="$work/bundle.out"
  (cd "$stage" && find . -type f -print | LC_ALL=C sort | zip -X -q -9 -@ "$bundle_file")
}

# --- pinned sources and tool versions ----------------------------------------
if [[ -n ${INFO_FILE:-} ]]; then
  cp "$INFO_FILE" "$work/info.txt"
else
  (cd "$board_dir" && ./build.sh info) >"$work/info.raw" 2>&1 || die "'./build.sh info' failed in $board_dir"
  # no machine-specific paths in a published manifest
  grep -v -E '^(Build dir|Work tree)' "$work/info.raw" | sed "s|$root|<repo>|g" >"$work/info.txt"
fi

: >"$work/tools.tsv"
tool() { local n=$1; shift; command -v "$1" >/dev/null 2>&1 || return 0; printf '%s\t%s\n' "$n" "$( ("$@" 2>&1 || true) | head -n1)" >>"$work/tools.tsv"; }
tool xz xz --version
tool bash bash --version
tool python3 python3 --version
tool git git --version
tool gcc gcc --version
tool make make --version
tool mmdebstrap mmdebstrap --version
tool fakeroot fakeroot --version
tool mke2fs mke2fs -V
tool sfdisk sfdisk --version
tool bmaptool bmaptool --version
tool ccache ccache --version
tool zip zip -v
tool tar tar --version
printf 'os\t%s\n' "$( (. /etc/os-release 2>/dev/null && echo "${PRETTY_NAME:-unknown}") || uname -sr)" >>"$work/tools.tsv"

# --- the assets ----------------------------------------------------------------
: >"$work/files.tsv"
case $kind_stage in
  jetson-kernel) stage_jetson_kernel ;;
  uuu-bundle)    stage_uuu_bundle ;;
  "")            ;;
  *)             die "unknown stage '$kind_stage' in images.json" ;;
esac

n_assets=0
while IFS=$'\t' read -r src name compress role optional; do
  if [[ $src == @bundle ]]; then
    in=$bundle_file
    [[ -n $in ]] || die "$name: variant has no stage that builds a bundle"
  else
    in="$deploy/$src"
    if [[ ! -e $in ]]; then
      [[ $optional == 1 ]] && { info "skipping optional $src (not built)"; continue; }
      die "missing $in: did the build finish? (images.json lists it as required)"
    fi
  fi
  raw_size=$(fsize "$in")
  raw_sha=$(sha256 "$in")
  case $compress in
    xz)   asset="$name.xz"; xz -T1 -6 -c <"$in" >"$outdir/$asset" ;;
    none) asset="$name";    cat "$in" >"$outdir/$asset" ;;
    *)    die "unknown compression '$compress' for $name" ;;
  esac
  size=$(fsize "$outdir/$asset")
  sha=$(sha256 "$outdir/$asset")
  printf '%s  %s\n' "$sha" "$asset" >"$outdir/$asset.sha256"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$asset" "$role" "$size" "$sha" "$name" "$raw_size" "$raw_sha" "$compress" >>"$work/files.tsv"
  info "$asset  $size bytes  sha256 ${sha:0:16}…"
  n_assets=$((n_assets + 1))
done < <(python3 "$here/matrix.py" --assets "$board" "$variant")
[[ $n_assets -gt 0 ]] || die "no assets were produced"

python3 "$here/write-manifest.py" --entry "$work/entry.json" --files "$work/files.tsv" --info "$work/info.txt" \
  --tools "$work/tools.tsv" --tag "$tag" --commit "$commit" --epoch "$sde" --out "$outdir/manifest.json"

python3 "$here/verify-assets.py" "$outdir"
info "wrote $n_assets asset(s) and manifest.json to $outdir"
