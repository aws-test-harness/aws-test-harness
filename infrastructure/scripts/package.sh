#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

build_directory_path="${1}"
distributable_directory_path="${2}"

rm -rf "${distributable_directory_path:?}"
mkdir -p "${distributable_directory_path}"

tar -czf "${distributable_directory_path}/infrastructure.tar.gz" -C "${build_directory_path}" .