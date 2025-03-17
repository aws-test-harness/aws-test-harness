#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

get_absolute_path() {
  local relative_path="$1"
  echo "${script_directory_path}/../${relative_path}"
}

build_directory_path="$(get_absolute_path build)"
assets_directory_path="${build_directory_path}/assets"

build_lambda_function_code_bundle() {
  local lambda_function_directory_relative_path="$1"

  echo "Building Lambda function code bundle for ${lambda_function_directory_relative_path}..." 1>&2

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

  local lambda_function_build_directory
  lambda_function_build_directory="${assets_directory_path}/${lambda_function_directory_relative_path}"
  mkdir -p "${lambda_function_build_directory}"

  local code_bundle_checksum
  code_bundle_checksum="$(cksum "${code_bundle_temp_file_path}" | cut -f 1 -d ' ')"

  local code_bundle_file_name
  code_bundle_file_name="${code_bundle_checksum}.zip"
  mv "${code_bundle_temp_file_path}" "${lambda_function_build_directory}/${code_bundle_file_name}"

  echo "${lambda_function_directory_relative_path}/${code_bundle_file_name}"
}

rm -rf "${build_directory_path:?}"
mkdir -p "${build_directory_path}"
cp "$(get_absolute_path src)"/* "${build_directory_path}"

mkdir -p "${assets_directory_path}"
echo "TEST_DOUBLES_MACRO_CODE_BUNDLE_PATH=$(build_lambda_function_code_bundle "macros/test-doubles")" >> "${build_directory_path}/install.env"
echo "TEST_DOUBLE_INVOCATION_HANDLER_FUNCTION_CODE_BUNDLE_PATH=$(build_lambda_function_code_bundle "invocation-handler")" >> "${build_directory_path}/install.env"

