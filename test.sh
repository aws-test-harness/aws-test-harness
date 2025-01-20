#!/usr/bin/env bash

echo Running tests...
uv run --frozen pytest tests
echo