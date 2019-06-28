#!/bin/bash
docker run -it --rm \
    --name lenovo-scrapper \
    -v "$HOME/localdata/lenovo-outlet-scrapper/example.db:/tmp/example.db" \
    -v "$HOME/localdata/lenovo-outlet-scrapper/data:/tmp/data" \
    lenovo-scrapper
