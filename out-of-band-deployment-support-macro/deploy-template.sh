#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail;

stack_name_prefix="${1:-}"
macro_name_prefix="${2:-}"

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cd "${script_directory_path}"

dist_directory=dist
rm -rf "${dist_directory}"
mkdir -p "${dist_directory}"

template_relative_path="template.yaml"
code_indent_whitespace="$(grep -E '^ *__CODE_PLACEHOLDER__' "${template_relative_path}" | grep -o '^ *')"

# Escape new lines and indent
code="$(awk -v prefix="${code_indent_whitespace}" '{gsub(/\\n/, "\\\\n"); printf "%s%s\\n", prefix, $0}' src/index.py)"

artifact_path="${dist_directory}/${template_relative_path}"
sed "s/^ *__CODE_PLACEHOLDER__/${code}/" "${template_relative_path}" > "${artifact_path}"

aws cloudformation deploy \
  --stack-name "${stack_name_prefix}out-of-band-deployment-support-macro" \
  --template-file "${artifact_path}" \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides MacroNamePrefix="${macro_name_prefix}"