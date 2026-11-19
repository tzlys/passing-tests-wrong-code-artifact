#!/usr/bin/env bash
# One-time setup on a fresh Amazon Linux 2023 x86_64 host (default user ec2-user).
# Uses only Amazon's own package repositories. SWE-bench needs Python >= 3.10, so python3.11.
set -euo pipefail
for i in 1 2 3; do
  sudo dnf install -y docker git tar python3.11 python3.11-pip && break
  echo "dnf retry $i"; sleep 20
done
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
python3.11 -m venv "$HOME/sbenv"
"$HOME/sbenv/bin/pip" install --upgrade pip
# Same SWE-bench release as all earlier runs (tag v4.1.0, commit 726c5461).
"$HOME/sbenv/bin/pip" install "git+https://github.com/SWE-bench/SWE-bench@v4.1.0"
echo "Setup done."
