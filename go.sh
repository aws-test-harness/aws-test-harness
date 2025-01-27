#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

echo Initializing virtual environment...
uv venv --allow-existing --seed
echo

echo Synchronizing virtual environment with lock file...
uv sync --all-packages
echo
