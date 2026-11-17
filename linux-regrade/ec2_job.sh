#!/bin/bash
# Runs on the EC2 host as a transient systemd service (started by the launcher's user-data),
# so package installs that restart services cannot kill it. Needs $COMMIT.
export HOME=/root USER=root DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l NEEDRESTART_SUSPEND=1
exec >> /var/log/stageb.log 2>&1
say() { echo "STAGEB-STATUS $*" | tee /dev/ttyS0; }
finish() {
  code=$?
  say "exit-$code"
  if [ ! -f /root/key.tgz ]; then
    tail -60 /var/log/stageb.log > /dev/ttyS0
    sleep 900                                # leave time to read the console
  fi
  systemctl poweroff
}
trap finish EXIT
# Watchdog: power off only if uptime passes 4 hours. If this loop is killed, nothing happens.
( while sleep 60; do [ "$(cut -d. -f1 /proc/uptime)" -gt 14400 ] && systemctl poweroff; done ) >/dev/null 2>&1 &
set -x
say started
say "net $(curl -s -o /dev/null -w '%{http_code}' https://github.com)"
apt-get update -y && apt-get install -y git || { say failed-apt; exit 1; }
git clone https://github.com/tzlys/passing-tests-wrong-code-artifact /root/repo || { say failed-clone; exit 1; }
cd /root/repo && git checkout "$COMMIT" && git rev-parse HEAD > /root/commit.txt || { say failed-checkout; exit 1; }
say setup
bash linux-regrade/setup_host.sh || { say failed-setup; exit 1; }
say regrade
bash linux-regrade/run_regrade.sh || say regrade-failed
RES=$(ls -d /root/stageb-linux-*/ 2>/dev/null | head -1)
mkdir -p /root/key && cp /root/commit.txt /root/key/
if [ -n "$RES" ]; then
  cd "$RES" && cp -r --parents summary.json dataset-check.json images.txt repo-commit.txt \
     $(ls logs/run_evaluation/*/*/*/report.json 2>/dev/null) /root/key/ 2>/dev/null
fi
tail -200 /var/log/stageb.log > /root/key/tail.log
tar czf /root/key.tgz.tmp -C /root key && mv /root/key.tgz.tmp /root/key.tgz
echo "STAGEB-BEGIN" > /dev/ttyS0
base64 -w 76 /root/key.tgz > /dev/ttyS0
echo "STAGEB-END" > /dev/ttyS0
sleep 20
