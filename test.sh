#!/usr/bin/env zsh
set -e
LOG_LEVEL=DEBUG PYTHONPATH=. uv run pytest tests -r fpE -s --log-level=INFO --tb=no "$@" 