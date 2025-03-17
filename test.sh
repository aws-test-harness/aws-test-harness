#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

./infrastructure/test.sh
./languages/python/test.sh

echo Running acceptance tests...
uv run --isolated pytest tests
echo