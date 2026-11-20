#!/bin/bash
# EXT-02 Stage 0. Run on the Mac (needs internet; no credentials; anonymous HTTPS reads only).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/ext02-probe}"
cd "$HERE"
python3 ext02_probe.py "$OUT"
echo "Probe done: $OUT"
