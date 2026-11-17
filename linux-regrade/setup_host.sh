#!/usr/bin/env bash
# One-time setup on a fresh Ubuntu 22.04 x86_64 EC2 host (run as the default user).
set -euo pipefail
sudo apt-get update -y
sudo apt-get install -y docker.io git python3-venv python3-pip jq
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
python3 -m venv "$HOME/sbenv"
"$HOME/sbenv/bin/pip" install --upgrade pip
# Same SWE-bench release whose specs the macOS admission used (tag v4.1.0, commit 726c5461).
"$HOME/sbenv/bin/pip" install "git+https://github.com/SWE-bench/SWE-bench@v4.1.0"
echo
echo "Setup done. Start a new shell so the docker group applies:  newgrp docker"
