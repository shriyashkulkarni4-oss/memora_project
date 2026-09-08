.PHONY: generate validate build push manifest up down local local-stop health test

PROFILE ?= full
VERSION ?= local
SHA ?= $(shell git rev-parse HEAD)
UV ?= uv

generate:
	$(UV) run python scripts/generate_runtime.py

validate: generate
	@for profile in infra app-only full temporal; do docker compose --env-file ../.env.example -f runtime/docker-compose.$$profile.yml config --quiet; done
	$(UV) run python -m unittest discover -s tests -p 'test_*.py'

build:
	$(UV) run python build/scripts/build_images.py --version $(VERSION) --sha $(SHA) --load

push:
	$(UV) run python build/scripts/build_images.py --version $(VERSION) --sha $(SHA) --push

manifest:
	$(UV) run python build/scripts/generate_image_manifest.py --version $(VERSION) --sha $(SHA)

up:
	runtime/manage_services_docker.sh start --profile $(PROFILE)

down:
	runtime/manage_services_docker.sh stop --profile $(PROFILE)

local:
	runtime/manage_services_local.sh start --profile $(PROFILE)

local-stop:
	runtime/manage_services_local.sh stop --profile $(PROFILE)

health:
	$(UV) run python health_checker/health_check.py --mode docker --profile $(PROFILE)

test:
	$(UV) run python -m unittest discover -s tests -p 'test_*.py'
