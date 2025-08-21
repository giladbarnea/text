#!/usr/bin/env zsh
if [[ -t 1 && -t 0 && "$USER" = giladbarnea && "$LOGNAME" = giladbarnea && "$CURSOR_AGENT" != 1 ]]; then
    uv run python -m pytest --color=yes --code-highlight=yes "$@"
else
    uv run python -m pytest --color=no --code-highlight=no -vv "$@"
fi