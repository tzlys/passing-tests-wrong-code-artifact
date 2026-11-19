#!/usr/bin/env bash
# EXT-01: show progress, or (when finished) copy results back and delete the AWS resources.
#
#   bash fetch_ext01_to_mac.sh            # progress, or fetch + clean up when done
#   ABORT=1 bash fetch_ext01_to_mac.sh    # copy whatever exists, then delete everything now
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
STATE="$HERE/ext01-state${SHARD:+-$SHARD}.env"
[ -f "$STATE" ] || { echo "No EXT-01 state file ($STATE); nothing is running for shard ${SHARD:-none}."; exit 0; }
# shellcheck disable=SC1090
source "$STATE"
A=(--region "$REGION")

stateof=$(aws ec2 describe-instances "${A[@]}" --instance-ids "$IID" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)
echo "instance $IID: $stateof"

cleanup_all() {
  aws ec2 terminate-instances "${A[@]}" --instance-ids "$IID" >/dev/null 2>&1
  aws ec2 wait instance-terminated "${A[@]}" --instance-ids "$IID" && echo "instance $IID terminated"
  aws ec2 delete-security-group "${A[@]}" --group-id "$SG" && echo "security group $SG deleted"
  aws ec2 delete-key-pair "${A[@]}" --key-name "$NAME" >/dev/null && echo "key pair $NAME deleted"
  rm -f "$KEY" "$STATE"
}

if [ "$stateof" != "running" ]; then
  echo "The instance is not running (fail-safe or manual stop). Results on it are gone; cleaning up the rest."
  cleanup_all; exit 0
fi

# Allow SSH from the Mac's current IP, in case it changed since launch.
MYIP=$(curl -s https://checkip.amazonaws.com | tr -d '[:space:]')
aws ec2 authorize-security-group-ingress "${A[@]}" --group-id "$SG" --protocol tcp --port 22 --cidr "$MYIP/32" >/dev/null 2>&1 || true
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$OUT/known_hosts" -o ConnectTimeout=15 "${RUSER:-ubuntu}@$IP")

echo "== progress"
"${SSH[@]}" 'cat ~/ext01-out/STATUS 2>/dev/null; tail -8 ~/ext01-out/progress.txt 2>/dev/null; uptime'

if "${SSH[@]}" 'test -f ~/ext01-out/DONE'; then
  echo "== finished: copying results"
  scp -i "$KEY" -o UserKnownHostsFile="$OUT/known_hosts" "${RUSER:-ubuntu}@$IP:~/ext01-results.tar.gz" "$OUT/" \
    && tar xzf "$OUT/ext01-results.tar.gz" -C "$OUT" \
    && { echo "== results"; cat "$OUT/ext01-out/RESULTS-EXT01.md" 2>/dev/null || tail -6 "$OUT/ext01-out/progress.txt"; cleanup_all; } \
    || echo "Copy failed; the instance is left running. Run this script again."
elif [ "${ABORT:-0}" = 1 ]; then
  echo "== aborting: copying partial outputs"
  "${SSH[@]}" 'cd ~ && tar czf ext01-partial.tar.gz --exclude=ext01-out/raw ext01-out' \
    && scp -i "$KEY" -o UserKnownHostsFile="$OUT/known_hosts" "${RUSER:-ubuntu}@$IP:~/ext01-partial.tar.gz" "$OUT/"
  cleanup_all
else
  echo "Still running. Run this script again later (or ABORT=1 to stop and clean up)."
fi
