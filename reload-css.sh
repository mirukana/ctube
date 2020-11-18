#!/usr/bin/env sh
set -e

mkdir -p src/static/css
echo src/styles/main.sass |
    entr -nr sassc src/styles/main.sass src/static/css/main.css
