.PHONY: generate validate build push manifest up down restart status logs runtime-validate rate-reset clean migrate seed smoke local local-stop local-restart local-status local-logs local-clean health health-local health-k8s test

PROFILE ?= full
NAMESPACE ?= cml-memoryhive-local
VERSION ?= local
SHA ?= $(shell git rev-parse HEAD)
UV ?= uv

generate:
	$(UV) run python scripts/generate_runtime.py

validate: generate
	@for profile in infra app-only full temporal; do docker compose --env-file ../.env.example -f runtime/docker-compose.$$profile.yml config --quiet; done
	$(UV) run python -m unittest discover -s tests -p 'test_*.py'

build: generate
	$(UV) run python build/scripts/build_images.py --version $(VERSION) --sha $(SHA) --load

push: generate
	$(UV) run python build/scripts/build_images.py --version $(VERSION) --sha $(SHA) --push

manifest: generate
	$(UV) run python build/scripts/generate_image_manifest.py --version $(VERSION) --sha $(SHA)

up:
	runtime/manage_services_docker.sh start --profile $(PROFILE)

down:
	runtime/manage_services_docker.sh stop --profile $(PROFILE)

restart:
	runtime/manage_services_docker.sh restart --profile $(PROFILE)

status:
	runtime/manage_services_docker.sh status --profile $(PROFILE)

logs:
	runtime/manage_services_docker.sh logs --profile $(PROFILE)

runtime-validate:
	runtime/manage_services_docker.sh validate --profile $(PROFILE)

rate-reset:
	runtime/manage_services_docker.sh rate-reset --profile $(PROFILE)

clean:
	runtime/manage_services_docker.sh clean --profile $(PROFILE)

migrate:
	runtime/manage_services_docker.sh migrate --profile $(PROFILE)

seed:
	runtime/manage_services_docker.sh seed --profile $(PROFILE) $(SEED_ARGS)

smoke:
	runtime/manage_services_docker.sh smoke --profile $(PROFILE)

local:
	runtime/manage_services_local.sh start --profile $(PROFILE)

local-stop:
	runtime/manage_services_local.sh stop --profile $(PROFILE)

local-restart:
	runtime/manage_services_local.sh restart --profile $(PROFILE)

local-status:
	runtime/manage_services_local.sh status --profile $(PROFILE)

local-logs:
	runtime/manage_services_local.sh logs --profile $(PROFILE)

local-clean:
	runtime/manage_services_local.sh clean --profile $(PROFILE)

health: generate
	$(UV) run python health_checker/health_check.py --mode docker --profile $(PROFILE)

health-local: generate
	$(UV) run python health_checker/health_check.py --mode local --profile $(PROFILE)

health-k8s: generate
	$(UV) run python health_checker/health_check.py --mode k8s --profile $(PROFILE) --namespace $(NAMESPACE)

test:
	$(UV) run python -m unittest discover -s tests -p 'test_*.py'
