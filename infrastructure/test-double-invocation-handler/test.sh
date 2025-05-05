#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

script_directory_path="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

"${script_directory_path}/function-code/test.sh"
"${script_directory_path}/infrastructure/test.sh"
