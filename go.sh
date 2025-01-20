#!/usr/bin/env bash

echo Initializing virtual environment...
uv venv --allow-existing --seed
echo

echo Synchronizing virtual environment with lock file...
uv sync --frozen
echo
