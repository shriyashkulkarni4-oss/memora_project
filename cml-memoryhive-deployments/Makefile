.PHONY: generate validate validate-all apply upgrade status rollback delete test

ENV ?= local
PROFILE ?= full
SECRET_ENV_FILE ?=
SECRET_ARG = $(if $(SECRET_ENV_FILE),--secret-env-file $(SECRET_ENV_FILE),)
UV ?= uv

generate:
	$(UV) run python scripts/manage.py generate $(ENV) $(PROFILE)

validate:
	$(UV) run python scripts/manage.py validate $(ENV) $(PROFILE)

validate-all:
	@for env in local staging production; do for profile in infra app-only full temporal; do $(UV) run python scripts/manage.py validate $$env $$profile; done; done

apply:
	$(UV) run python scripts/manage.py apply $(ENV) $(PROFILE) $(SECRET_ARG)

upgrade:
	$(UV) run python scripts/manage.py upgrade $(ENV) $(PROFILE) $(SECRET_ARG)

status:
	$(UV) run python scripts/manage.py status $(ENV) $(PROFILE)

rollback:
	$(UV) run python scripts/manage.py rollback $(ENV) $(PROFILE) $(DEPLOYMENT)

delete:
	$(UV) run python scripts/manage.py delete $(ENV) $(PROFILE)

test:
	$(UV) run python -m unittest discover -s tests -p 'test_*.py'
