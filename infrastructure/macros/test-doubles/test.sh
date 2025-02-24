#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

script_directory_path="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo Running test-doubles macro tests...
uv run --directory "${script_directory_path}" pytest "${script_directory_path}/tests"
echo