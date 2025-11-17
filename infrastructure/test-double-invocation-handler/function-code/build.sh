#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

build_directory_path="${1}"

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

source "${script_directory_path}/../../scripts/lib/lambda.bash"

rm -rf "${build_directory_path:?}"
mkdir -p "${build_directory_path}"

__lambda__build_function_code_asset "${script_directory_path}" "${build_directory_path}"