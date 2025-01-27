#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

./go.sh
./lint.sh
./test.sh