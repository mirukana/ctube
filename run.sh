#!/usr/bin/env sh

mkdir -p ctube/static/css || exit 1

while true; do
    find ctube -type f -not -name 'main.css' -not -path '*__pycache__*' |
    entr -cdnr sh -c \
        "sassc ctube/styles/main.sass ctube/static/css/main.css && sleep 0.2 && killall -9 uvicorn; uvicorn ctube:APP $*"
done
