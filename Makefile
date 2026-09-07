.PHONY: build-images build-manifest runtime-generate runtime-up runtime-down runtime-local health-local k8s-generate k8s-validate k8s-status k8s-upgrade goal-2-test

PROFILE ?= full
K8S_ENV ?= local
K8S_PROFILE ?= full
IMAGE_VERSION ?= local
IMAGE_SHA ?= $(shell git rev-parse HEAD)

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
	python3 cml-memoryhive-build/health_checker/health_check.py --mode local --profile $(PROFILE)

k8s-generate:
	$(MAKE) -C cml-memoryhive-deployments generate ENV=$(K8S_ENV) PROFILE=$(K8S_PROFILE)

k8s-validate:
	$(MAKE) -C cml-memoryhive-deployments validate ENV=$(K8S_ENV) PROFILE=$(K8S_PROFILE)

k8s-status:
	$(MAKE) -C cml-memoryhive-deployments status ENV=$(K8S_ENV) PROFILE=$(K8S_PROFILE)

k8s-upgrade:
	$(MAKE) -C cml-memoryhive-deployments upgrade ENV=$(K8S_ENV) PROFILE=$(K8S_PROFILE)

goal-2-test:
	$(MAKE) -C cml-memoryhive-build test
	$(MAKE) -C cml-memoryhive-deployments test
	python3 scripts/audit_project_naming.py
