#!/usr/bin/env sh
set -e

cd src
mkdir -p static/css
sassc styles/main.sass static/css/main.css
uvicorn main:app --reload
