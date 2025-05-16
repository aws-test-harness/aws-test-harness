#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

script_directory_path="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo Running Python library unit tests...
uv run --isolated --directory "${script_directory_path}" pytest "${script_directory_path}/tests/aws_test_harness_tests/unit"
echo

echo Running Python library integration tests...
uv run --isolated --directory "${script_directory_path}" pytest "${script_directory_path}/tests/aws_test_harness_tests/integration"
echo

echo Running Python library acceptance tests...
uv run --isolated --directory "${script_directory_path}" pytest "${script_directory_path}/tests/aws_test_harness_tests/acceptance"
echo