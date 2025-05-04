#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

script_directory_path="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

test_source_directory_path="${script_directory_path}/tests/invocation_handler_code_tests"

echo Running invocation handler unit tests...
uv run --isolated --directory "${script_directory_path}" pytest "${test_source_directory_path}/unit"
echo

echo Running invocation handler integration tests...
uv run --isolated --directory "${script_directory_path}" pytest "${test_source_directory_path}/integration"
echo