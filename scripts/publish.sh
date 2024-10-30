#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail;

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cd "${script_directory_path}/.."

rm -rf dist && uv build && uv publish --token "${PYPI_TOKEN}"