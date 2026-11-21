#!/bin/sh
if command -v clear >/dev/null 2>&1; then
    exec clear "$@"
else
    printf '\033[2J\033[3J\033[H'
fi
