#!/usr/bin/env bash
# Regenerate every SVG in docs/images/ from its Python generator.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
for g in boot_chain build_pipeline sd_layout fip_anatomy memory_map uboot_flow scmi_flow source_map stack_compare sd_layout_st; do
  python3 "$g.py"
done
