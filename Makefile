.PHONY: build-images build-manifest runtime-generate runtime-up runtime-down runtime-local health-local k8s-generate k8s-validate k8s-status k8s-upgrade goal-2-test goal-2-readiness

PROFILE ?= full
K8S_ENV ?= local
K8S_PROFILE ?= full
IMAGE_VERSION ?= local
IMAGE_SHA ?= $(shell git rev-parse HEAD)
UV ?= uv

build-images:
	$(MAKE) -C cml-memoryhive-build build VERSION=$(IMAGE_VERSION) SHA=$(IMAGE_SHA)

build-manifest:
	$(MAKE) -C cml-memoryhive-build manifest VERSION=$(IMAGE_VERSION) SHA=$(IMAGE_SHA)

runtime-generate:
	$(MAKE) -C cml-memoryhive-build generate

runtime-up:
	$(MAKE) -C cml-memoryhive-build up PROFILE=$(PROFILE)

runtime-down:
	$(MAKE) -C cml-memoryhive-build down PROFILE=$(PROFILE)

runtime-local:
	$(MAKE) -C cml-memoryhive-build local PROFILE=$(PROFILE)

health-local:
	$(MAKE) -C cml-memoryhive-build health-local PROFILE=$(PROFILE)

k8s-generate:
	$(MAKE) -C cml-memoryhive-deployments generate ENV=$(K8S_ENV) PROFILE=$(K8S_PROFILE)

k8s-validate:
	$(MAKE) -C cml-memoryhive-deployments validate ENV=$(K8S_ENV) PROFILE=$(K8S_PROFILE)

k8s-status:
	$(MAKE) -C cml-memoryhive-deployments status ENV=$(K8S_ENV) PROFILE=$(K8S_PROFILE)

k8s-upgrade:
	$(MAKE) -C cml-memoryhive-deployments upgrade ENV=$(K8S_ENV) PROFILE=$(K8S_PROFILE)

goal-2-test:
	cd cml-memoryhive-backend && $(UV) run ruff check app tests && $(UV) run black --check app tests && $(UV) run pytest -q
	npm --prefix cml-memoryhive-frontend run lint
	npm --prefix cml-memoryhive-frontend test
	npm --prefix cml-memoryhive-frontend run build
	npm --prefix cml-memoryhive-mobile run typecheck
	npm --prefix cml-memoryhive-mobile run lint
	npm --prefix cml-memoryhive-mobile test
	$(MAKE) -C cml-memoryhive-build validate
	docker compose --env-file .env.production.example -f cml-memoryhive-build/runtime/docker-compose.production.yml config --quiet
	$(MAKE) -C cml-memoryhive-deployments test
	$(MAKE) -C cml-memoryhive-deployments validate-all
	npm --prefix cml-memoryhive-automation run dry-run
	$(UV) run python scripts/audit_project_naming.py
	$(UV) run python scripts/generate_knowledge.py --check

goal-2-readiness: goal-2-test
	$(MAKE) -C cml-memoryhive-deployments readiness-all
