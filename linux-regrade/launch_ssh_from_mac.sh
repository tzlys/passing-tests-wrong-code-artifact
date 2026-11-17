#!/usr/bin/env bash
# AMENDMENT-02 Linux regrading over SSH, with live output in your terminal.
#
#   bash launch_ssh_from_mac.sh          # region defaults to us-east-2
#
# Uses your existing AWS CLI login. It creates, for this run only:
# - a key pair (the private key stays in this folder and is deleted at the end);
# - a security group that allows SSH from your current IP only;
# - one m5.xlarge Ubuntu 22.04 x86_64 instance with a 100 GB disk.
# No automatic power-off is installed. On exit (success, failure or Ctrl-C)
# it terminates the instance and deletes the security group and the key pair.
set -euo pipefail
REGION="${REGION:-us-east-2}"
TYPE="${TYPE:-m5.xlarge}"
COMMIT="${COMMIT:-main}"
HERE="$(cd "$(dirname "$0")" && pwd)"
NAME="stageb-$(date +%s)"
OUT="$HERE/results-$(date -u +%Y%m%dT%H%M%SZ)"
KEY="$HERE/.$NAME.pem"
mkdir -p "$OUT"
A=(--region "$REGION")
IID=""; SG=""

cleanup() {
  set +e
  echo; echo "== cleanup"
  if [ -n "$IID" ]; then
    aws ec2 terminate-instances "${A[@]}" --instance-ids "$IID" >/dev/null
    aws ec2 wait instance-terminated "${A[@]}" --instance-ids "$IID" && echo "instance $IID terminated"
  fi
  [ -n "$SG" ] && aws ec2 delete-security-group "${A[@]}" --group-id "$SG" && echo "security group $SG deleted"
  aws ec2 delete-key-pair "${A[@]}" --key-name "$NAME" >/dev/null && echo "key pair $NAME deleted"
  rm -f "$KEY"
}
trap cleanup EXIT

AMI=$(aws ec2 describe-images "${A[@]}" --owners 099720109477 \
  --filters 'Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*' 'Name=state,Values=available' \
  --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text)
VPC=$(aws ec2 describe-vpcs "${A[@]}" --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
MYIP=$(curl -s https://checkip.amazonaws.com | tr -d '[:space:]')
echo "region=$REGION type=$TYPE ami=$AMI vpc=$VPC myip=$MYIP"

aws ec2 create-key-pair "${A[@]}" --key-name "$NAME" --query KeyMaterial --output text > "$KEY"
chmod 600 "$KEY"
SG=$(aws ec2 create-security-group "${A[@]}" --group-name "$NAME" --description "stageb regrade ssh" \
  --vpc-id "$VPC" --query GroupId --output text)
aws ec2 authorize-security-group-ingress "${A[@]}" --group-id "$SG" --protocol tcp --port 22 --cidr "$MYIP/32" >/dev/null

IID=$(aws ec2 run-instances "${A[@]}" --image-id "$AMI" --instance-type "$TYPE" \
  --key-name "$NAME" --security-group-ids "$SG" \
  --instance-initiated-shutdown-behavior terminate \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=stageb-linux-regrade}]' \
  --query 'Instances[0].InstanceId' --output text)
echo "instance=$IID"; echo "$IID" > "$OUT/instance-id.txt"
aws ec2 wait instance-running "${A[@]}" --instance-ids "$IID"
IP=$(aws ec2 describe-instances "${A[@]}" --instance-ids "$IID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "ip=$IP; waiting for SSH"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$OUT/known_hosts" \
     -o ServerAliveInterval=30 -o ConnectTimeout=10 "ubuntu@$IP")
for i in $(seq 1 30); do "${SSH[@]}" true 2>/dev/null && break; sleep 10; done

echo "== remote run (live output)"
"${SSH[@]}" "COMMIT=$COMMIT bash -s" <<'REMOTE' 2>&1 | tee "$OUT/remote.log"
set -x
uptime
git clone https://github.com/tzlys/passing-tests-wrong-code-artifact ~/repo
cd ~/repo && git checkout "$COMMIT" && git rev-parse HEAD
bash linux-regrade/setup_host.sh
echo "== setup finished; uptime: $(uptime)"
sg docker -c "bash linux-regrade/run_regrade.sh"
echo "== regrade finished; uptime: $(uptime)"
ls -la ~/stageb-linux-*.tar.gz
REMOTE

echo "== copy results back"
scp -i "$KEY" -o UserKnownHostsFile="$OUT/known_hosts" "ubuntu@$IP:~/stageb-linux-*.tar.gz" "$OUT/"
for f in "$OUT"/stageb-linux-*.tar.gz; do tar xzf "$f" -C "$OUT"; done
S=$(ls "$OUT"/stageb-linux-*/summary.json 2>/dev/null | head -1)
[ -n "$S" ] && { echo "== summary"; cat "$S"; }
