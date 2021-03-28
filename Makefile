# HELP
# This will output the help for each task
# thanks to https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.PHONY: help

help: ## This help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help

build: ## Build the development docker images
	# @docker-compose build --no-cache
	docker-compose build --force-rm --parallel

clean: ## Stop and remove a running containers
	docker-compose down --remove-orphans && docker-compose rm

run: ## Stop and remove a running containers
	make clean && make build && docker-compose up --remove-orphans

shell: ## Get Shell access session inside the API container
	docker-compose run --rm api bash

test: ## Run tests
	docker-compose run --rm data-api pytest -v

coverage: ## Run coverage
	docker-compose run --rm data-api sh -c "pytest --cov-config .coveragerc --cov=./src"


lint: ## Run lint
	docker-compose run --rm data-api pre-commit run --all-files
