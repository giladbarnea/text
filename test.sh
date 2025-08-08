#!/usr/bin/env zsh
set -e
PYTHONPATH=. tests/test_extract_toc.py --tb=no -r fpE "$@" 