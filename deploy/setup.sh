#!/usr/bin/env bash
# One-time setup for the fde_gh_deploy user on the deploy runner.
set -euo pipefail

loginctl enable-linger "$(whoami)"
sudo mkdir -p /opt/techassist
sudo chown -R "$(whoami):$(whoami)" /opt/techassist
python3 -m venv /opt/techassist/venv
