#!/usr/bin/env bash
# EXT-01 stage 2 (detached, hours): official harness runs M and G per entry, confirmation reruns, analysis.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$HOME/sbenv/bin/python"
OUT="$HOME/ext01-out"
cd "$OUT"
exec >> "$OUT/console.log" 2>&1
echo "running" > STATUS
log() { echo "$(date -u +%FT%TZ) $*" | tee -a progress.txt; }
harness() {  # dataset preds run_id
  "$PY" -m swebench.harness.run_evaluation --dataset_name "$1" --split test --predictions_path "$2" \
    --max_workers "${WORKERS:-12}" --run_id "$3" --cache_level env --timeout 900 --report_dir reports \
    || log "harness exit $? for $3"
}
mkdir -p reports
mapfile -t ENTRIES < <(ls data/*.jsonl | xargs -n1 basename | sed 's/\.jsonl$//' | sort)
log "stage2 start: ${#ENTRIES[@]} entries"
k=0
for e in "${ENTRIES[@]}"; do
  k=$((k+1)); n=$(wc -l < "data/$e.jsonl")
  log "[$k/${#ENTRIES[@]}] $e ($n records) M"
  harness "$OUT/data/$e.jsonl" "$OUT/preds/$e.M.jsonl" "ext01-$k-M"
  log "[$k/${#ENTRIES[@]}] $e G"
  harness "$OUT/data/$e.jsonl" gold "ext01-$k-G"
  docker container prune -f >/dev/null; docker image prune -a -f >/dev/null
  log "[$k/${#ENTRIES[@]}] done; disk $(df -h / | awk 'NR==2{print $5}')"
done
log "phase1 analysis"
"$PY" "$REPO/linux-regrade/ext01/ext01_analyze.py" "$OUT" phase1 | tee -a progress.txt
k=0
for e in "${ENTRIES[@]}"; do
  k=$((k+1))
  [ -f "rerun/data/$e.jsonl" ] || continue
  log "rerun [$k] $e"
  harness "$OUT/rerun/data/$e.jsonl" "$OUT/rerun/preds/$e.M.jsonl" "ext01-$k-M-rep"
  harness "$OUT/rerun/data/$e.jsonl" gold "ext01-$k-G-rep"
  docker container prune -f >/dev/null; docker image prune -a -f >/dev/null
done
log "final analysis"
"$PY" "$REPO/linux-regrade/ext01/ext01_analyze.py" "$OUT" final | tee -a progress.txt
cd "$HOME"
tar czf ext01-results.tar.gz \
  --exclude='ext01-out/raw' --exclude='*/run_instance.log' --exclude='*/image_build_dir' ext01-out
log "packed $(du -h ext01-results.tar.gz | cut -f1)"
echo "done" > "$OUT/STATUS"; touch "$OUT/DONE"
