#!/usr/bin/env bash
# Regenerate every generated SVG diagram in the repository.
#
# Each docs/images/_src/ directory holds a kit.py (the drawing helpers) and one generator per
# diagram. Hand-drawn SVGs are not touched. CI runs this and fails if it changes a committed file,
# so the SVGs always match their generators.
set -euo pipefail
TOP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
count=0
while IFS= read -r kit; do
  src="$(dirname "$kit")"
  for gen in "$src"/*.py; do
    case "$(basename "$gen")" in kit.py | add_icons.py) continue ;; esac
    # only files that call write(...) are generators
    grep -q '^write(' "$gen" || continue
    (cd "$src" && python3 "$(basename "$gen")" >/dev/null)
    count=$((count + 1))
  done
done < <(find "$TOP" -path '*/docs/images/_src/kit.py' -not -path '*/build/*')
echo "regenerated diagrams from $count generators"
