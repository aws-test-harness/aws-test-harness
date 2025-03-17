#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

get_absolute_path() {
  local relative_path="$1"
  echo "${script_directory_path}/../${relative_path}"
}

build_directory_path="$(get_absolute_path build)"
assets_directory_path="${build_directory_path}/assets"

build_asset() {
  local source_file_path="$1"
  local assets_directory_path="$2"
  local assets_subdirectory_path="$3"

  local code_bundle_checksum
  code_bundle_checksum="$(cksum "${source_file_path}" | cut -f 1 -d ' ')"

  local asset_file_name
  asset_file_name="${code_bundle_checksum}.zip"

  local asset_relative_file_path
  asset_relative_file_path="${assets_subdirectory_path}/${asset_file_name}"

  mkdir -p "${assets_directory_path}/${assets_subdirectory_path}"
  cp "${source_file_path}" "${assets_directory_path}/${asset_relative_file_path}"

  echo "${asset_relative_file_path}"
}

rm -rf "${build_directory_path:?}"
mkdir -p "${build_directory_path}"
cp "$(get_absolute_path src)"/* "${build_directory_path}"

mkdir -p "${assets_directory_path}"

function common_build_steps() {
  local project_relative_path="$1"

  local project_directory_path
  project_directory_path="$(get_absolute_path "${project_relative_path}")"

  local code_path
  code_path="$("${project_directory_path}"/build.sh)"

  build_asset "${code_path}" "${assets_directory_path}" "${project_relative_path}"
}

echo "TEST_DOUBLES_MACRO_CODE_BUNDLE_PATH=$(common_build_steps macros/test-doubles)" >> "${build_directory_path}/install.env"
echo "TEST_DOUBLE_INVOCATION_HANDLER_FUNCTION_CODE_BUNDLE_PATH=$(common_build_steps invocation-handler)" >> "${build_directory_path}/install.env"