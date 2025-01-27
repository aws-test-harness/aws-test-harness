#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

echo Running tests...
uv run pytest tests
echo