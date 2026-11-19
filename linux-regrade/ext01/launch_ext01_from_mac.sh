#!/usr/bin/env bash
# EXT-01 launcher: AWS keeps working after your Mac sleeps.
#
#   COMMIT=<sha> bash launch_ext01_from_mac.sh     # start (Mac must be awake ~15 min)
#   bash fetch_ext01_to_mac.sh                     # later: shows progress, or fetches results and cleans up
#
# Uses your existing AWS CLI login. It creates one m5.4xlarge Amazon Linux 2023 instance
# with a 300 GB disk, a key pair (private key kept in this folder until fetch) and a
# security group that allows SSH from your current IP only.
# Fail-safe: the instance powers off and is TERMINATED automatically 14 hours after
# start, whether or not results were fetched. If anything fails before the long
# stage is detached, everything is deleted immediately.
set -euo pipefail
REGION="${REGION:-us-east-2}"
TYPE="${TYPE:-m5.4xlarge}"
COMMIT="${COMMIT:?set COMMIT to the repository commit to run}"
HERE="$(cd "$(dirname "$0")" && pwd)"
STATE="$HERE/ext01-state.env"
[ -e "$STATE" ] && { echo "An EXT-01 instance seems to exist already ($STATE). Run fetch_ext01_to_mac.sh first."; exit 1; }
NAME="ext01-$(date +%s)"
OUT="$HERE/results-ext01-$(date -u +%Y%m%dT%H%M%SZ)"
KEY="$HERE/.$NAME.pem"
mkdir -p "$OUT"
A=(--region "$REGION")
IID=""; SG=""; DETACHED=0

cleanup() {
  [ "$DETACHED" = 1 ] && return
  set +e
  echo; echo "== failure before detaching: cleaning up"
  if [ -n "$IID" ]; then
    aws ec2 terminate-instances "${A[@]}" --instance-ids "$IID" >/dev/null
    aws ec2 wait instance-terminated "${A[@]}" --instance-ids "$IID" && echo "instance $IID terminated"
  fi
  [ -n "$SG" ] && aws ec2 delete-security-group "${A[@]}" --group-id "$SG" && echo "security group $SG deleted"
  aws ec2 delete-key-pair "${A[@]}" --key-name "$NAME" >/dev/null && echo "key pair $NAME deleted"
  rm -f "$KEY" "$STATE"
}
trap cleanup EXIT

echo "== probe: public S3 logs readable without credentials?"
# No pipe into head here: under pipefail an early-closing head makes aws fail with SIGPIPE.
if ! PROBE=$(aws s3 ls "s3://swe-bench-submissions/lite/20250526_sweagent_claude-4-sonnet-20250514/logs/" --no-sign-request 2>&1); then
  printf '%s\n' "${PROBE:0:400}"
  echo "Cannot list the public bucket anonymously; EXT-01 cannot run as designed."; exit 1
fi
printf 'probe ok: %s\n' "${PROBE:0:200}"

# Amazon Linux 2023: its package repositories are hosted by AWS (Ubuntu mirrors were inconsistent on 2026-11-19).
AMI=$(aws ec2 describe-images "${A[@]}" --owners amazon \
  --filters 'Name=name,Values=al2023-ami-2023.*-kernel-*-x86_64' 'Name=state,Values=available' \
  --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text)
RUSER=ec2-user
VPC=$(aws ec2 describe-vpcs "${A[@]}" --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
MYIP=$(curl -s https://checkip.amazonaws.com | tr -d '[:space:]')
echo "region=$REGION type=$TYPE ami=$AMI vpc=$VPC myip=$MYIP commit=$COMMIT"

aws ec2 create-key-pair "${A[@]}" --key-name "$NAME" --query KeyMaterial --output text > "$KEY"
chmod 600 "$KEY"
SG=$(aws ec2 create-security-group "${A[@]}" --group-name "$NAME" --description "ext01 ssh" \
  --vpc-id "$VPC" --query GroupId --output text)
aws ec2 authorize-security-group-ingress "${A[@]}" --group-id "$SG" --protocol tcp --port 22 --cidr "$MYIP/32" >/dev/null
IID=$(aws ec2 run-instances "${A[@]}" --image-id "$AMI" --instance-type "$TYPE" \
  --key-name "$NAME" --security-group-ids "$SG" \
  --instance-initiated-shutdown-behavior terminate \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":300,"VolumeType":"gp3","Iops":6000,"Throughput":500,"DeleteOnTermination":true}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ext01}]' \
  --query 'Instances[0].InstanceId' --output text)
echo "instance=$IID"
aws ec2 wait instance-running "${A[@]}" --instance-ids "$IID"
IP=$(aws ec2 describe-instances "${A[@]}" --instance-ids "$IID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
cat > "$STATE" <<EOS
REGION=$REGION
NAME=$NAME
IID=$IID
SG=$SG
IP=$IP
KEY=$KEY
OUT=$OUT
RUSER=$RUSER
EOS
echo "ip=$IP; waiting for SSH"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$OUT/known_hosts" \
     -o ServerAliveInterval=30 -o ConnectTimeout=10 "$RUSER@$IP")
for i in $(seq 1 30); do "${SSH[@]}" true 2>/dev/null && break; sleep 10; done

echo "== remote setup and stage 1 (live output)"
"${SSH[@]}" "COMMIT=$COMMIT bash -s" <<'REMOTE' 2>&1 | tee "$OUT/remote-stage1.log"
set -ex
sudo shutdown -h +840 "EXT-01 fail-safe: terminating 14 h after start"
for i in 1 2 3; do sudo dnf install -y git && break; sleep 20; done
git clone https://github.com/tzlys/passing-tests-wrong-code-artifact ~/repo
cd ~/repo && git checkout "$COMMIT" && git rev-parse HEAD
bash linux-regrade/setup_host_al2023.sh
sg docker -c "bash linux-regrade/ext01/ext01_stage1.sh"
REMOTE
[ "${PIPESTATUS[0]}" = 0 ] || { echo "stage 1 failed"; exit 1; }

echo "== starting stage 2 detached"
"${SSH[@]}" 'sg docker -c "nohup setsid bash ~/repo/linux-regrade/ext01/ext01_stage2.sh > ~/ext01-stage2.nohup 2>&1 < /dev/null &"; sleep 5; cat ~/ext01-out/STATUS; tail -3 ~/ext01-out/progress.txt'
DETACHED=1
echo
echo "Stage 2 is running on AWS. Your Mac can sleep now."
echo "Check progress or fetch results later with:  bash $HERE/fetch_ext01_to_mac.sh"
echo "Fail-safe: the instance terminates itself about 14 h from now."
