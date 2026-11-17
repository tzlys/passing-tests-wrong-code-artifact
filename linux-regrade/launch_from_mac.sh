#!/usr/bin/env bash
# Run the whole AMENDMENT-02 Linux regrading from your Mac with your existing AWS CLI login.
#
#   bash launch_from_mac.sh            # region defaults to us-east-2
#
# What it does:
# - Starts ONE on-demand Ubuntu 22.04 x86_64 instance: m5.xlarge, 100 GB gp3,
#   with no inbound access.
# - The instance clones this repository at a fixed commit and runs
#   setup_host.sh and run_regrade.sh. It then prints the key results to its
#   serial console and shuts itself down. Shutdown terminates the instance and
#   deletes its disk.
# - There is a hard stop after 4 hours either way.
# - This script polls the console, saves the results next to itself, and
#   finally calls terminate-instances again, to be sure.
#
# No SSH, no key pair, no S3 and no new IAM entity are used. Credentials stay
# in your AWS CLI.
set -euo pipefail
REGION="${REGION:-us-east-2}"
TYPE="${TYPE:-m5.xlarge}"
COMMIT="${COMMIT:-main}"   # commit that holds the regrading scripts
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/results-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"

AMI="${AMI:-}"
[ -z "$AMI" ] && AMI=$(aws ssm get-parameter --region "$REGION" \
  --name /aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id \
  --query Parameter.Value --output text 2>/dev/null || true)
[ -z "$AMI" ] || [ "$AMI" = "None" ] && AMI=$(aws ec2 describe-images --region "$REGION" --owners 099720109477 \
  --filters 'Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*' 'Name=state,Values=available' \
  --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text)
echo "region=$REGION type=$TYPE ami=$AMI"

cat > "$OUT/user-data.sh" <<EOF
#!/bin/bash
exec > /var/log/stageb.log 2>&1
( sleep 14400; poweroff ) >/dev/null 2>&1 &   # hard stop after 4 hours (a plain timer, not a scheduled shutdown)
export HOME=/root USER=root DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a
say() { echo "\$@" > /dev/ttyS0; }
say "STAGEB-STATUS started"
fail() { say "STAGEB-STATUS failed-\$1"; tail -40 /var/log/stageb.log > /dev/ttyS0; sleep 900; shutdown -h now; exit 1; }
say "STAGEB-STATUS net \$(curl -s -o /dev/null -w '%{http_code}' https://github.com)"
apt-get update -y && apt-get install -y git || fail apt
git clone https://github.com/tzlys/passing-tests-wrong-code-artifact /root/repo || fail clone
cd /root/repo && git checkout $COMMIT && git rev-parse HEAD > /root/commit.txt || fail checkout
say "STAGEB-STATUS setup"
bash linux-regrade/setup_host.sh || fail setup
say "STAGEB-STATUS regrade"
bash linux-regrade/run_regrade.sh || say "STAGEB-STATUS regrade-failed"
RES=\$(ls -d /root/stageb-linux-*/ 2>/dev/null | head -1)
mkdir -p /root/key && cp /root/commit.txt /root/key/
[ -n "\$RES" ] && cd "\$RES" && cp -r --parents summary.json dataset-check.json images.txt repo-commit.txt \
   \$(ls logs/run_evaluation/*/*/*/report.json 2>/dev/null) /root/key/ 2>/dev/null
tail -200 /var/log/stageb.log > /root/key/tail.log
tar czf /root/key.tgz -C /root key
say "STAGEB-BEGIN"
base64 -w 76 /root/key.tgz > /dev/ttyS0
say "STAGEB-END"
sleep 20
shutdown -h now
EOF

IID=$(aws ec2 run-instances --region "$REGION" --image-id "$AMI" --instance-type "$TYPE" \
  --instance-initiated-shutdown-behavior terminate \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=stageb-linux-regrade}]' \
  --user-data "file://$OUT/user-data.sh" --query 'Instances[0].InstanceId' --output text)
echo "instance=$IID   (started $(date))"
echo "$IID" > "$OUT/instance-id.txt"
aws ec2 describe-instances --region "$REGION" --instance-ids "$IID" \
  --query 'Reservations[0].Instances[0].{subnet:SubnetId,vpc:VpcId,publicIp:PublicIpAddress,state:State.Name}' --output text
trap 'echo; echo "terminating $IID"; aws ec2 terminate-instances --region "$REGION" --instance-ids "$IID" >/dev/null' EXIT

for i in $(seq 1 270); do               # up to ~4.5 hours
  sleep 60
  C=$(aws ec2 get-console-output --region "$REGION" --instance-id "$IID" --latest --output text --query Output 2>/dev/null || true)
  S=$(printf '%s' "$C" | grep -o 'STAGEB-STATUS [a-z-]*' | tail -1 || true)
  STATE=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$IID" --query 'Reservations[0].Instances[0].State.Name' --output text)
  printf '\r[%3d min] %-30s state=%-12s' "$i" "${S:-booting}" "$STATE"
  if printf '%s' "$C" | grep -q 'STAGEB-END'; then
    printf '%s' "$C" | tr -d '\r' | sed -n '/STAGEB-BEGIN/,/STAGEB-END/p' | sed '1d;$d' | base64 --decode > "$OUT/key.tgz"
    tar xzf "$OUT/key.tgz" -C "$OUT"
    echo; echo "results saved in $OUT/key"
    [ -f "$OUT/key/summary.json" ] && cat "$OUT/key/summary.json" | head -80
    exit 0
  fi
  [ -n "$C" ] && printf '%s' "$C" > "$OUT/console-latest.txt"
  if [ "$STATE" = "shutting-down" ] || [ "$STATE" = "terminated" ]; then
    echo; echo "instance ended without results."
    aws ec2 describe-instances --region "$REGION" --instance-ids "$IID" \
      --query 'Reservations[0].Instances[0].{reason:StateReason,transition:StateTransitionReason,subnet:SubnetId,publicIp:PublicIpAddress}' | tee "$OUT/state-reason.json"
    echo "console tail:"; tail -40 "$OUT/console-latest.txt" 2>/dev/null; exit 1; fi
done
echo; echo "timed out waiting for results"; exit 1
