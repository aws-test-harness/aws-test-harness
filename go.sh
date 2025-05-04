#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

echo Initializing virtual environment...
uv venv --allow-existing --seed
echo

echo Synchronizing virtual environment with lock file...
uv sync --all-packages
echo

aws_profile="$(jq -r '.awsProfile' config.json)"

if [[ -z "${aws_profile}" ]] || [[ "${aws_profile}" == "null" ]]; then
  echo "Error: AWS SSO profile not defined in config.json"
  exit 1
fi

echo Logging into AWS SSO profile...
aws sso login --profile "${aws_profile}"
echo