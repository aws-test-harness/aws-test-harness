#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

./languages/python/test.sh

echo Running acceptance tests...
uv run pytest tests
echo