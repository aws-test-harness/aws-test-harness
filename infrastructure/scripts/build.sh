#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

get_absolute_path() {
  local relative_path="$1"
  echo "${script_directory_path}/../${relative_path}"
}

function build_asset() {
  local project_relative_path="$1"
  local assets_directory_path="$2"

  local project_directory_path
  project_directory_path="$(get_absolute_path "${project_relative_path}")"

  local code_bundle_path
  code_bundle_path="$("${project_directory_path}"/build.sh)"

  local code_bundle_checksum
  code_bundle_checksum="$(cksum "${code_bundle_path}" | cut -f 1 -d ' ')"

  local asset_file_name
  asset_file_name="${code_bundle_checksum}.zip"

  local asset_relative_file_path
  asset_relative_file_path="${project_relative_path}/${asset_file_name}"

  mkdir -p "${assets_directory_path}/${project_relative_path}"
  cp -a "${code_bundle_path}" "${assets_directory_path}/${asset_relative_file_path}"

  echo "${asset_relative_file_path}"
}

build_directory_path="$(get_absolute_path build)"
rm -rf "${build_directory_path:?}"
mkdir -p "${build_directory_path}"

cp "$(get_absolute_path src)"/* "${build_directory_path}"

assets_directory_path="${build_directory_path}/assets"
mkdir -p "${assets_directory_path}"

echo "TEST_DOUBLES_MACRO_CODE_BUNDLE_PATH=$(build_asset macros/test-doubles "${assets_directory_path}")" >> "${build_directory_path}/install.env"
# TODO: Ensure we exit if the first command fails
echo "TEST_DOUBLE_INVOCATION_HANDLER_FUNCTION_CODE_BUNDLE_PATH=$(build_asset invocation-handler "${assets_directory_path}")" >> "${build_directory_path}/install.env"