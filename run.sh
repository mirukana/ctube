#!/usr/bin/env sh

mkdir -p heretube/static/css || exit 1

while true; do
    find heretube -type f -not -name 'main.css' -not -path '*__pycache__*' |
    entr -cdnr sh -c \
        "sassc heretube/styles/main.sass heretube/static/css/main.css && sleep 0.2 && killall -9 uvicorn; uvicorn heretube:APP $*"
done
