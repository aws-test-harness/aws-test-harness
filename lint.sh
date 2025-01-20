#!/usr/bin/env bash

echo Typing checking...
uv run --frozen mypy .
echo

echo Linting...
uv run --frozen ruff check .
echo