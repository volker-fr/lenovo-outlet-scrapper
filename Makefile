#!/bin/bash .PHONY: help
mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
repo_dir := $(patsubst %/,%,$(dir $(mkfile_path)))



help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

cwd := $(shell pwd)

build:   ## Build docker container
	docker build -t lenovo-scrapper .

run: build ## Run docker container
	docker run -it --rm \
		--name lenovo-scrapper \
		-v "${repo_dir}/example.db:/tmp/example.db" \
		-v "${repo_dir}/lenovo-outlet-scrapper/data:/tmp/data" \
		lenovo-scrapper

shell: build  ## Debug docker container by opening a shell in a new container
	docker run -it --rm \
		--entrypoint=/bin/bash \
		lenovo-scrapper
