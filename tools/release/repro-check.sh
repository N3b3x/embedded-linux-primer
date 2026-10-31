#!/usr/bin/env bash
# =============================================================================
#  tools/release/repro-check.sh - build the cheap parts of a board twice and compare the results
# =============================================================================
#
#  Usage:  tools/release/repro-check.sh <board-dir> <commands> <outputs>
#            commands  one build command per line, run inside the board directory
#            outputs   space-separated file names in build/deploy/ to compare
#
#  Each run gets its own copy of the board directory under a different path (a/ and b/), starting from the
#  same downloads and toolchain, so differences caused by the build path, by timestamps or by run order show
#  up. SOURCE_DATE_EPOCH is set to the same value in both. Prints a Markdown report on stdout (for the job
#  summary). Exit status: 0 when the outputs are identical, 3 when they differ, 1 when a build failed.
# =============================================================================
set -Eeuo pipefail

[[ $# -eq 3 ]] || { sed -n '5,10p' "$0" | sed 's/^#  \{0,1\}//' >&2; exit 2; }
boarddir=$(cd "$1" && pwd) cmds=$2 outputs=$3
work=${REPRO_WORK:-$(mktemp -d)}
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git -C "$boarddir" log -1 --format=%ct 2>/dev/null || echo 0)}

sha256() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

for run in a b; do
  dest="$work/$run/$(basename "$boarddir")"
  rm -rf "${work:?}/$run"
  mkdir -p "$dest/build"
  tar -C "$boarddir" --exclude=./build -cf - . | tar -C "$dest" -xf -
  for keep in downloads toolchain; do
    [[ -d $boarddir/build/$keep ]] && cp -a "$boarddir/build/$keep" "$dest/build/$keep"
  done
  while IFS= read -r c; do
    [[ -n $c ]] || continue
    echo "[$run] $c" >&2
    (cd "$dest" && bash -c "$c") >&2 || { echo "build failed in run $run: $c" >&2; exit 1; }
  done <<<"$cmds"
done

status=0
echo "| File | Run A sha256 | Run B sha256 | Identical |"
echo "| --- | --- | --- | --- |"
for f in $outputs; do
  pa="$work/a/$(basename "$boarddir")/build/deploy/$f" pb="$work/b/$(basename "$boarddir")/build/deploy/$f"
  if [[ ! -f $pa || ! -f $pb ]]; then
    echo "| \`$f\` | missing | missing | **no** |"
    status=1
    continue
  fi
  ha=$(sha256 "$pa") hb=$(sha256 "$pb")
  if [[ $ha == "$hb" ]]; then
    echo "| \`$f\` | \`${ha:0:16}…\` | \`${hb:0:16}…\` | yes |"
  else
    echo "| \`$f\` | \`${ha:0:16}…\` | \`${hb:0:16}…\` | **NO** ($(cmp -l "$pa" "$pb" 2>/dev/null | wc -l | tr -d ' ') bytes differ) |"
    [[ $status -eq 1 ]] || status=3
  fi
done
exit "$status"
