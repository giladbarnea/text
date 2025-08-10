#!/usr/bin/env zsh
set -e
PYTHONPATH=. uv run pytest tests -r fpE "$@" 