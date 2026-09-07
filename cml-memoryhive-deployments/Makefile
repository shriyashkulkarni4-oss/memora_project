.PHONY: generate validate validate-all apply upgrade status rollback delete test

ENV ?= local
PROFILE ?= full
SECRET_ENV_FILE ?=
SECRET_ARG = $(if $(SECRET_ENV_FILE),--secret-env-file $(SECRET_ENV_FILE),)

generate:
	python3 scripts/manage.py generate $(ENV) $(PROFILE)

validate:
	python3 scripts/manage.py validate $(ENV) $(PROFILE)

validate-all:
	@for env in local staging production; do for profile in infra app-only full temporal; do python3 scripts/manage.py validate $$env $$profile; done; done

apply:
	python3 scripts/manage.py apply $(ENV) $(PROFILE) $(SECRET_ARG)

upgrade:
	python3 scripts/manage.py upgrade $(ENV) $(PROFILE) $(SECRET_ARG)

status:
	python3 scripts/manage.py status $(ENV) $(PROFILE)

rollback:
	python3 scripts/manage.py rollback $(ENV) $(PROFILE) $(DEPLOYMENT)

delete:
	python3 scripts/manage.py delete $(ENV) $(PROFILE)

test:
	python3 -m unittest discover -s tests -p 'test_*.py'
