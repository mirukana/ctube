#!/usr/bin/env sh
set -e
cd src
sassc styles/main.sass static/css/main.css
uvicorn main:app --reload
