#!/usr/bin/env sh
set -e
mkdir -p ctube/static/css
pysassc --style expanded ctube/styles/main.sass ctube/static/css/main.css
uvicorn ctube:APP "$@"
