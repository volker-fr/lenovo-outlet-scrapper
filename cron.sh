#!/bin/bash
DOCKER_NAME=lenovo-scrapper

if docker ps|grep "$DOCKER_NAME" > /dev/null; then
    if docker ps -f name="$DOCKER_NAME" --format '{{ .RunningFor }}'|grep "[1-9][0-9] min" > /dev/null; then
        echo "process is running for a while"
        docker ps -f name="$DOCKER_NAME" --format '{{ .RunningFor }}' || true
        docker kill "$DOCKER_NAME"
    elif docker ps -f name="$DOCKER_NAME" --format '{{ .RunningFor }}'|grep "hour" > /dev/null; then
        echo "process is running for a while"
        docker ps -f name="$DOCKER_NAME" --format '{{ .RunningFor }}' || true
        docker kill "$DOCKER_NAME"
    fi

    # docker is running already
    exit
fi



docker run --rm \
    --name lenovo-scrapper \
    -v "$HOME/localdata/lenovo-outlet-scrapper/example.db:/tmp/example.db" \
    -v "$HOME/localdata/lenovo-outlet-scrapper/data:/tmp/data" \
    lenovo-scrapper
