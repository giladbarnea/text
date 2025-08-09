#!/usr/bin/env zsh
set -e
PYTHONPATH=. uv run pytest tests --tb=no -r fpE "$@" 