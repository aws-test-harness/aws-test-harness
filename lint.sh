#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

fix_linting=0

while getopts ":f" opt; do
  case $opt in
    f)
      fix_linting=1
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done


if [[ "${fix_linting}" -eq 1 ]]; then
  echo "Fixing linting..."
  uv run ruff check --fix .
  exit 0
fi

echo Type checking...
uv run mypy
echo

echo Linting...
uv run ruff check .
echo
