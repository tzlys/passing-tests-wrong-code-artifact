#!/usr/bin/env bash
# One-time setup on a fresh Ubuntu 22.04 x86_64 EC2 host (run as the default user).
set -euo pipefail

apt_update_ok() {
  # Success only when every index fetched; apt-get exits 0 even when a mirror returns 503.
  local log; log=$(sudo apt-get -o Acquire::Retries=5 update 2>&1) || { printf '%s\n' "$log"; return 1; }
  printf '%s\n' "$log"
  ! grep -qE '^(W: Failed to fetch|E: )' <<<"$log"
}
if ! apt_update_ok; then
  echo "== regional Ubuntu mirror failed; switching to archive.ubuntu.com"
  sudo sed -i -E 's#http://[a-z0-9.-]*\.ec2\.archive\.ubuntu\.com/ubuntu#http://archive.ubuntu.com/ubuntu#g' /etc/apt/sources.list
  for i in 1 2 3; do apt_update_ok && break; echo "apt update retry $i"; sleep 20; done
fi
sudo apt-get -o Acquire::Retries=5 install -y docker.io git python3-venv python3-pip jq
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
python3 -m venv "$HOME/sbenv"
"$HOME/sbenv/bin/pip" install --upgrade pip
# Same SWE-bench release whose specs the macOS admission used (tag v4.1.0, commit 726c5461).
"$HOME/sbenv/bin/pip" install "git+https://github.com/SWE-bench/SWE-bench@v4.1.0"
echo
echo "Setup done. Start a new shell so the docker group applies:  newgrp docker"
