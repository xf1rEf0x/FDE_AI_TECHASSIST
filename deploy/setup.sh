#!/usr/bin/env bash
# One-time setup for the fde_gh_deploy user on the deploy runner.
set -euo pipefail

loginctl enable-linger "$(whoami)"
mkdir -p /opt/techassist
python3 -m venv /opt/techassist/venv
