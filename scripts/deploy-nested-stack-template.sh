#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail;

nested_stack_name="${1}"
templates_s3_bucket="${2}"

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cd "${script_directory_path}/../templates/${nested_stack_name}"

template_relative_path="template.yaml"
artifact_path="${template_relative_path}"

if grep -q '__CODE_PLACEHOLDER__' "${template_relative_path}"; then
  code_indent_whitespace="$(grep -E '^ *__CODE_PLACEHOLDER__' "${template_relative_path}" | grep -o '^ *')"

  # Escape new lines and indent
  code="$(awk -v prefix="${code_indent_whitespace}" '{gsub(/\\n/, "\\\\n"); printf "%s%s\\n", prefix, $0}' src/index.py)"

  dist_directory=dist
  rm -rf "${dist_directory}"
  mkdir -p "${dist_directory}"
  artifact_path="${dist_directory}/${template_relative_path}"

  sed "s/^ *__CODE_PLACEHOLDER__/${code}/" "${template_relative_path}" > "${artifact_path}"
fi

aws s3 cp "${artifact_path}" "s3://${templates_s3_bucket}/${nested_stack_name}/"