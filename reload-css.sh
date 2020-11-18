#!/usr/bin/env sh
set -e
echo src/styles/main.sass |
    entr -nr sassc src/styles/main.sass src/static/css/main.css
