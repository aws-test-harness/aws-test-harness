#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

get_absolute_path() {
  local relative_path="$1"
  echo "${script_directory_path}/../${relative_path}"
}

build_directory_path="$(get_absolute_path build)"

# TODO: Extract as shared function for use by different projects
build_lambda_function_code_bundle() {
  local lambda_function_directory_relative_path="$1"
  local target_directory_path="$2"

  local working_directory_path
  working_directory_path="$(mktemp -d)"
  cp -r "$(get_absolute_path "${lambda_function_directory_relative_path}")/src/" "${working_directory_path}"
  find "${working_directory_path}" -exec touch -t 198001010000 {} +

  local code_bundle_temp_file_path
  code_bundle_temp_file_path="$(mktemp).zip"

  pushd "${working_directory_path}" > /dev/null
  zip -qr "${code_bundle_temp_file_path}" .
  popd > /dev/null

  touch -t 198001010000 "${code_bundle_temp_file_path}"

  mv "${code_bundle_temp_file_path}" "${target_directory_path}/code.zip"
}

rm -rf "${build_directory_path:?}"
mkdir -p "${build_directory_path}"

build_lambda_function_code_bundle "." "${build_directory_path}"