#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail;

source_template_file_path="${1}"
destination_template_file_path="${2}"

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cd "${script_directory_path}/.."

working_template_file_path="$(mktemp)"

cp "${source_template_file_path}" "${working_template_file_path}"

leading_whitespace_pattern='^ *'
code_placeholder_path_prefix_pattern="${leading_whitespace_pattern}__CODE_PLACEHOLDER__:"
code_placeholder_pattern="${code_placeholder_path_prefix_pattern}.+"

if grep -q -E "${code_placeholder_pattern}" "${working_template_file_path}"; then
  grep -E "${code_placeholder_pattern}" "${working_template_file_path}" | while IFS= read -r code_placeholder_line; do
    # Extract placeholder indentation and code file path
    code_indent_whitespace="$(grep -o -E "${leading_whitespace_pattern}" <<< "${code_placeholder_line}")"
    relative_code_file_path="$(sed -E "s@${code_placeholder_path_prefix_pattern}@@" <<< "${code_placeholder_line}")"
    code_file_path="$(dirname "${source_template_file_path}")/${relative_code_file_path}"

    # Escape new lines and indent
    code="$(awk -v prefix="${code_indent_whitespace}" '{gsub(/\\n/, "\\\\n"); printf "%s%s\\n", prefix, $0}' "${code_file_path}")"

    # Replace the placeholder with the code
    sed -i "" "s~${code_placeholder_line}~${code}~" "${working_template_file_path}"
  done
fi

mv "${working_template_file_path}" "${destination_template_file_path}"