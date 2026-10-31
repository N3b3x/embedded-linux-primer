#!/usr/bin/env bash
# Regenerate every SVG in docs/images/ from its Python generator.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
for g in boot_chain build_pipeline sd_layout fip_anatomy memory_map uboot_flow scmi_flow source_map mp1_vs_mp2; do
  python3 "$g.py"
done
