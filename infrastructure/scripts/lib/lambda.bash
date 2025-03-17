function __lambda__build_function_code_asset() {
  local lambda_function_directory_path="$1"
  local target_directory_path="$2"

  local working_directory_path
  working_directory_path="$(mktemp -d)"
  cp -r "${lambda_function_directory_path}/src/" "${working_directory_path}"
  find "${working_directory_path}" -exec touch -t 198001010000 {} +

  local code_bundle_file_path
  code_bundle_file_path="$(mktemp).zip"

  # shellcheck disable=SC2164
  pushd "${working_directory_path}" > /dev/null
  zip -qr "${code_bundle_file_path}" .
  # shellcheck disable=SC2164
  popd > /dev/null

  touch -t 198001010000 "${code_bundle_file_path}"

  local target_file_path
  target_file_path="${target_directory_path}/code.zip"
  mv "${code_bundle_file_path}" "${target_file_path}"

  echo "${target_file_path}"
}