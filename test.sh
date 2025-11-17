#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

search_path="${1:-.}"

cleanup() {
    pkill -TERM -g $$ || true
}
trap cleanup SIGINT SIGTERM EXIT

test_paths="$(find "${search_path}"/**/* -type f -name test.sh -exec dirname {} + | xargs -0)"
# shellcheck disable=SC2086
bin/parallel-test ${test_paths}