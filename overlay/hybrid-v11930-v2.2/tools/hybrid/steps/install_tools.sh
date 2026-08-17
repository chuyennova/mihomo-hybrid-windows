#!/usr/bin/env bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y ca-certificates curl unzip zip
sudo update-ca-certificates
curl --version
unzip -v | head -n2
zip -v | head -n2
