# Brittle hack for determining uv workspace root directory
function __lambda__find_uv_workspace_root_directory() {
  # shellcheck disable=SC2016
  uv lock --dry-run --verbose 2>&1 | grep 'Found workspace root' | head -1 | sed -E 's/.*Found workspace root: `(.+)`.*/\1/'
}

function __lambda__build_function_code_asset() {
  local lambda_function_directory_path="$1"
  local target_directory_path="$2"

  echo "Building code asset for lambda function at ${lambda_function_directory_path}..." >&2

  local working_directory_path
  working_directory_path="$(mktemp -d)"

  # shellcheck disable=SC2164
  pushd "${lambda_function_directory_path}" > /dev/null
  echo "Installing packages..." >&2
  # Cargo expects HOME to be set
  HOME=~
  # Ensure uv is on path
  . $HOME/.cargo/env
  uv export --no-header --no-hashes --frozen --no-emit-project --no-dev > "${working_directory_path}/requirements.txt"
  uv_workspace_root_directory="$(__lambda__find_uv_workspace_root_directory)"
  # Include editable dependencies in requirements.txt
  grep -v '^-e ./' "${working_directory_path}/requirements.txt" > "${working_directory_path}/non-editable-requirements.txt"
  uv pip install --target "${working_directory_path}" --requirements "${working_directory_path}/non-editable-requirements.txt" > /dev/null
  grep '^-e ./' "${working_directory_path}/requirements.txt" | sed 's@-e \./@'"${uv_workspace_root_directory}"/'@' > "${working_directory_path}/editable-requirements.txt"
  # --no-deps avoids pip creating .pth files to editable transitive dependencies
  uv --no-cache pip install --no-deps --target "${working_directory_path}" --requirements "${working_directory_path}/editable-requirements.txt" > /dev/null
  rm "${working_directory_path}/requirements.txt" "${working_directory_path}/non-editable-requirements.txt" "${working_directory_path}/editable-requirements.txt" "${working_directory_path}/.lock"
  # shellcheck disable=SC2164
  popd > /dev/null

  echo "Copying source..." >&2
  cp -r "${lambda_function_directory_path}/src/" "${working_directory_path}"
  find "${working_directory_path}" \( -type f -name "*.pyc" -o -type d -name "__pycache__" \) -delete
  find "${working_directory_path}" -exec touch -t 198001010000 {} +

  local code_bundle_file_path
  code_bundle_file_path="$(mktemp).zip"

  # shellcheck disable=SC2164
  pushd "${working_directory_path}" > /dev/null
  echo "Creating zip..." >&2
  zip -qr "${code_bundle_file_path}" .
  touch -t 198001010000 "${code_bundle_file_path}"
  # shellcheck disable=SC2164
  popd > /dev/null

  local target_file_path
  target_file_path="${target_directory_path}/code.zip"
  mv "${code_bundle_file_path}" "${target_file_path}"

  echo "${target_file_path}"
  echo "" >&2
}