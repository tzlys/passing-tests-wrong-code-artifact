#!/usr/bin/env bash
# SUPPLEMENT-01 (post-hoc): rerun the flask-4045 recheck row whose test file lived
# outside the repository, with that file recovered from the session record.
# Run on the EC2 host after setup_host.sh:  bash linux-regrade/run_supplement_01.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$HOME/sbenv/bin/python"
OUT="$HOME/stageb-linux-supp01-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT" && cd "$OUT"
exec > >(tee -a "$OUT/console.log") 2>&1
echo "== host"; uname -a; docker version --format '{{.Server.Version}}'
tar xzf "$REPO/packages/stage-b-review-artifact.tar.gz"
ART="$OUT/stage-b-review-artifact"
( cd "$ART" && "$PY" -I -B review_stage_b.py | tail -1 )
"$PY" -I "$REPO/linux-regrade/supplement_01_recheck_4045.py" "$ART" "$OUT"
git -C "$REPO" rev-parse HEAD > "$OUT/repo-commit.txt"
rm -rf "$ART"
cd "$HOME" && tar czf "$OUT.tar.gz" "$(basename "$OUT")"
echo; echo "DONE: $OUT.tar.gz"
