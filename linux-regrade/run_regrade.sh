#!/usr/bin/env bash
# AMENDMENT-02: model-free Linux regrading and recheck of the Stage B pilot.
# Run on the EC2 host from a clone of this repository, after setup_host.sh:
#   bash linux-regrade/run_regrade.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$HOME/sbenv/bin/python"
OUT="$HOME/stageb-linux-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT" && cd "$OUT"
exec > >(tee -a "$OUT/console.log") 2>&1
IDS="psf__requests-3362 pallets__flask-4045 pallets__flask-4992"

echo "== host"; uname -a; docker version --format '{{.Server.Version}}'; "$PY" -m pip show swebench | sed -n 1,3p
tar xzf "$REPO/packages/stage-b-review-artifact.tar.gz"
ART="$OUT/stage-b-review-artifact"
( cd "$ART" && "$PY" -I -B review_stage_b.py | tail -1 )

echo "== dataset check"; "$PY" "$REPO/linux-regrade/check_dataset.py" "$ART" "$OUT/dataset-check.json"
"$PY" "$REPO/linux-regrade/make_predictions.py" "$ART" "$OUT/predictions-model.jsonl"

echo "== official harness: model patches"
"$PY" -m swebench.harness.run_evaluation --dataset_name princeton-nlp/SWE-bench_Lite --split test \
  --instance_ids $IDS --predictions_path "$OUT/predictions-model.jsonl" \
  --max_workers 3 --run_id stageb-model --cache_level instance --timeout 1800
echo "== official harness: reference patches (sanity)"
"$PY" -m swebench.harness.run_evaluation --dataset_name princeton-nlp/SWE-bench_Lite --split test \
  --instance_ids $IDS --predictions_path gold \
  --max_workers 3 --run_id stageb-gold --cache_level instance --timeout 1800

echo "== Linux recheck"; "$PY" "$REPO/linux-regrade/linux_recheck.py" "$ART" "$OUT"
echo "== compare"; "$PY" "$REPO/linux-regrade/compare.py" "$ART" "$OUT"
docker images --digests --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Digest}}' | grep sweb > "$OUT/images.txt" || true
git -C "$REPO" rev-parse HEAD > "$OUT/repo-commit.txt"
rm -rf "$ART"
cd "$HOME" && tar czf "$OUT.tar.gz" "$(basename "$OUT")"
echo; echo "DONE. Copy back to your Mac:  $OUT.tar.gz"
