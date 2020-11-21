#!/usr/bin/env sh

mkdir -p ything/static/css || exit 1

while true; do
    find ything -type f -not -name 'main.css' -not -path '*__pycache__*' |
    entr -cdnr sh -c \
        "sassc ything/styles/main.sass ything/static/css/main.css && sleep 0.2 && killall -9 uvicorn && uvicorn ything:APP $*"
done
