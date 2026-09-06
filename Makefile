.PHONY: build-images build-manifest health-local k8s-generate k8s-validate k8s-status k8s-upgrade

K8S_ENV ?= local
K8S_PROFILE ?= full
IMAGE_VERSION ?= local
IMAGE_SHA ?= $(shell git rev-parse HEAD)

build-images:
	python3 build/scripts/build_images.py --version $(IMAGE_VERSION) --sha $(IMAGE_SHA) --load

build-manifest:
	python3 build/scripts/generate_image_manifest.py --version $(IMAGE_VERSION) --sha $(IMAGE_SHA)

health-local:
	python3 health_checker/health_check.py --mode local backend frontend db redis minio

k8s-generate:
	python3 k8s/scripts/manage.py generate $(K8S_ENV) $(K8S_PROFILE)

k8s-validate:
	python3 k8s/scripts/manage.py validate $(K8S_ENV) $(K8S_PROFILE)

k8s-status:
	python3 k8s/scripts/manage.py status $(K8S_ENV) $(K8S_PROFILE)

k8s-upgrade:
	python3 k8s/scripts/manage.py upgrade $(K8S_ENV) $(K8S_PROFILE)
