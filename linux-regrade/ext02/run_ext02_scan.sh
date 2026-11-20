#!/bin/bash
# EXT-02 Stage 1. Run only after ext02_extract.py has been committed.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/ext02-out}"
cd "$HERE"
python3 ext02_metrics.py | tail -1
python3 ext02_scan.py "$OUT"
echo "Scan done: $OUT"
