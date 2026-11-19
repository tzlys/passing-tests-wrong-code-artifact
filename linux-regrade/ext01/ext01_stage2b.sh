#!/usr/bin/env bash
# EXT-01 stage 2b (detached): rerun the entries whose first run lost records to Docker Hub
# pull failures, spread over several hosts (each with its own pull quota).
#
#   SHARD_ENTRIES="4 5"           entry indices (1-based, sorted data/*.jsonl) to run fully: M, G, phase 1, reruns
#   REP_EXTRA="1:iid 3:iid"       first-run divergent records (entry index:instance id) to rerun for confirmation
#
# Changes from stage 2, all infrastructure: every needed image is pulled once, sequentially
# and with retries, before the harness starts; images are never pruned; 6 workers instead of 12.
# Sampling and classification rules are unchanged.
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
    --max_workers 6 --run_id "$3" --cache_level env --timeout 900 --report_dir reports \
    || log "harness exit $? for $3"
}
image_of() { echo "swebench/sweb.eval.x86_64.$(echo "$1" | tr 'A-Z' 'a-z' | sed 's/__/_1776_/'):latest"; }
quota() {  # Docker Hub anonymous quota; HEAD requests do not count as pulls
  local tok; tok=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:ratelimitpreview/test:pull" | "$PY" -c 'import json,sys;print(json.load(sys.stdin)["token"])')
  curl -s --head -H "Authorization: Bearer $tok" https://registry-1.docker.io/v2/ratelimitpreview/test/manifests/latest \
    | tr -d '\r' | grep -i '^ratelimit-' | tr '\n' ' '
}
prepull() {  # instance ids...
  for iid in "$@"; do
    img=$(image_of "$iid")
    docker image inspect "$img" >/dev/null 2>&1 && continue
    for t in 1 2 3; do
      docker pull -q "$img" >/dev/null 2>>pull-errors.txt && { log "pulled $img"; break; }
      log "pull failed ($t) $img: $(tail -1 pull-errors.txt)"; sleep $((30 * t))
    done
  done
}
mkdir -p reports
mapfile -t ENTRIES < <(ls data/*.jsonl | xargs -n1 basename | sed 's/\.jsonl$//' | sort)
log "stage2b start: entries [${SHARD_ENTRIES:-}] extra reps [${REP_EXTRA:-}]; quota: $(quota)"

ids_of() { "$PY" -c "import json,sys;print(' '.join(json.loads(l)['instance_id'] for l in open(sys.argv[1])))" "$1"; }
# 1. pull everything this shard needs, once
need=()
for k in ${SHARD_ENTRIES:-}; do need+=($(ids_of "data/${ENTRIES[$((k-1))]}.jsonl")); done
for x in ${REP_EXTRA:-}; do need+=("${x#*:}"); done
prepull $(printf '%s\n' "${need[@]}" | sort -u)
log "prepull done; quota: $(quota)"

# 2. full runs for the shard's entries
for k in ${SHARD_ENTRIES:-}; do
  e=${ENTRIES[$((k-1))]}
  log "[$k] $e M"; harness "$OUT/data/$e.jsonl" "$OUT/preds/$e.M.jsonl" "ext01-$k-M"
  log "[$k] $e G"; harness "$OUT/data/$e.jsonl" gold "ext01-$k-G"
done
log "phase1 analysis"
"$PY" "$REPO/linux-regrade/ext01/ext01_analyze.py" "$OUT" phase1 | tee -a progress.txt

# 3. confirmation reruns: divergent records of this shard's entries (from phase 1) ...
for k in ${SHARD_ENTRIES:-}; do
  e=${ENTRIES[$((k-1))]}
  [ -f "rerun/data/$e.jsonl" ] || continue
  log "rerun [$k] $e"
  harness "$OUT/rerun/data/$e.jsonl" "$OUT/rerun/preds/$e.M.jsonl" "ext01-$k-M-rep"
  harness "$OUT/rerun/data/$e.jsonl" gold "ext01-$k-G-rep"
done
# ... and first-run divergent records handed over explicitly
mkdir -p extra/data extra/preds
for x in ${REP_EXTRA:-}; do
  k=${x%%:*}; iid=${x#*:}; e=${ENTRIES[$((k-1))]}
  "$PY" - "$e" "$iid" <<'PY'
import json, sys
e, iid = sys.argv[1:3]
row = [l for l in open(f'data/{e}.jsonl') if json.loads(l)['instance_id'] == iid]
pred = [l for l in open(f'preds/{e}.M.jsonl') if json.loads(l)['instance_id'] == iid]
assert len(row) == 1 and len(pred) == 1, (e, iid)
open(f'extra/data/{e}.jsonl', 'a').write(row[0])
open(f'extra/preds/{e}.M.jsonl', 'a').write(pred[0])
PY
done
k=0
for e in "${ENTRIES[@]}"; do
  k=$((k+1))
  [ -f "extra/data/$e.jsonl" ] || continue
  log "extra rerun [$k] $e"
  harness "$OUT/extra/data/$e.jsonl" "$OUT/extra/preds/$e.M.jsonl" "ext01-$k-M-rep"
  harness "$OUT/extra/data/$e.jsonl" gold "ext01-$k-G-rep"
done
log "done; quota: $(quota)"
cd "$HOME"
tar czf ext01-results.tar.gz --exclude='ext01-out/raw' --exclude='*/image_build_dir' ext01-out
log "packed $(du -h ext01-results.tar.gz | cut -f1)"
echo "done" > "$OUT/STATUS"; touch "$OUT/DONE"
