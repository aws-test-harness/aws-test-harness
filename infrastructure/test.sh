#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

script_directory_path="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
"${script_directory_path}/test-double-invocation-handler/test.sh"
"${script_directory_path}/macros/test-doubles/test.sh"
"${script_directory_path}/acceptance-tests/test.sh"