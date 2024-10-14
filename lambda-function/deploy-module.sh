#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail;

script_directory="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cd "${script_directory}"

fragment_directory=fragments
rm -rf "${fragment_directory}"
mkdir -p "${fragment_directory}"

code_indent_whitespace="$(grep -E '^ *__CODE_PLACEHOLDER__' module.yaml | grep -o '^ *')"

# Escape new lines and indent
code="$(awk -v prefix="${code_indent_whitespace}" '{printf "%s%s\\n", prefix, $0}' src/index.py)"

sed "s/^ *__CODE_PLACEHOLDER__/${code}/" module.yaml > "${fragment_directory}/module.yaml"

cfn submit --set-default