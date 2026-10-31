#!/usr/bin/env bash
# Regenerate every SVG in docs/images/ from its Python generator.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
for g in boot_chain build_pipeline sd_layout bootbin_anatomy source_map ps_pl_map zmod_loading; do
  python3 "$g.py"
done
