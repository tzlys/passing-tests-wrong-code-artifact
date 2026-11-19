#!/usr/bin/env bash
# EXT-01 stage 1 (foreground, a few minutes): download public patches, screen, sample.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$HOME/sbenv/bin/python"
OUT="$HOME/ext01-out"
mkdir -p "$OUT" && cd "$OUT"
exec > >(tee -a "$OUT/console.log") 2>&1
echo "== stage1 start $(date -u +%FT%TZ)"; uname -a; docker version --format '{{.Server.Version}}'
"$PY" -m pip install -q boto3
"$PY" -m pip show swebench | sed -n 1,2p
git -C "$REPO" rev-parse HEAD > "$OUT/repo-commit.txt"
"$PY" "$REPO/linux-regrade/ext01/ext01_screen.py" "$REPO/linux-regrade/ext01" "$OUT"
echo "== stage1 done $(date -u +%FT%TZ)"
