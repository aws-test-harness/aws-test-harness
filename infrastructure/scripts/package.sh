#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

distributable_directory_path="${script_directory_path}/../dist"

rm -rf "${distributable_directory_path:?}"
mkdir -p "${distributable_directory_path}"

tar -czf "${distributable_directory_path}/infrastructure.tar.gz" -C "${script_directory_path}/../build" .