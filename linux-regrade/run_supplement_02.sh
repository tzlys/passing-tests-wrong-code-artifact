#!/usr/bin/env bash
# SUPPLEMENT-02 (post-hoc): run the model-written tests against the reference fix.
# Run on the EC2 host after setup_host.sh:  bash linux-regrade/run_supplement_02.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$HOME/sbenv/bin/python"
OUT="$HOME/stageb-linux-supp02-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT" && cd "$OUT"
exec > >(tee -a "$OUT/console.log") 2>&1
echo "== host"; uname -a; docker version --format '{{.Server.Version}}'
tar xzf "$REPO/packages/stage-b-review-artifact.tar.gz"
ART="$OUT/stage-b-review-artifact"
( cd "$ART" && "$PY" -I -B review_stage_b.py | tail -1 )
"$PY" -I "$REPO/taxonomy/verify_taxonomy.py" "$ART" | tail -1
"$PY" -I "$REPO/linux-regrade/supplement_02_agent_tests_under_reference.py" "$ART" "$OUT" \
  "$REPO/linux-regrade/supplement-01-2026-11-18/recovered-test_nested_blueprints.linux.py"
git -C "$REPO" rev-parse HEAD > "$OUT/repo-commit.txt"
rm -rf "$ART"
cd "$HOME" && tar czf "$OUT.tar.gz" "$(basename "$OUT")"
echo; echo "DONE: $OUT.tar.gz"
