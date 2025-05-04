#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

./go.sh -n
./lint.sh
./test.sh