#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

echo Type checking...
uv run --frozen mypy .
echo

echo Linting...
uv run --frozen ruff check .
echo
