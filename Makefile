# /!\ /!\ /!\ /!\ /!\ /!\ /!\ DISCLAIMER /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\
#
# This Makefile is only meant to be used for DEVELOPMENT purpose as we are
# changing the user id that will run in the container.
#
# PLEASE DO NOT USE IT FOR YOUR CI/PRODUCTION/WHATEVER...
#
# /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\
#
# Note to developers:
#
# While editing this file, please respect the following statements:
#
# 1. Every variable should be defined in the ad hoc VARIABLES section with a
#    relevant subsection
# 2. Every new rule should be defined in the ad hoc RULES section with a
#    relevant subsection depending on the targeted service
# 3. Rules should be sorted alphabetically within their section
# 4. When a rule has multiple dependencies, you should:
#    - duplicate the rule name to add the help string (if required)
#    - write one dependency per line to increase readability and diffs
# 5. .PHONY rule statement should be written after the corresponding rule
# ==============================================================================
# VARIABLES

BOLD := \033[1m
RESET := \033[0m
GREEN := \033[1;32m


# -- Database

DB_HOST                 = postgresql
DB_PORT                 = 5432

# -- Docker
# Get the current user ID to use for docker run and docker exec commands
DOCKER_UID              = $(shell id -u)
DOCKER_GID              = $(shell id -g)
DOCKER_USER             = $(DOCKER_UID):$(DOCKER_GID)
COMPOSE                 = DOCKER_USER=$(DOCKER_USER) docker compose
COMPOSE_EXEC            = $(COMPOSE) exec
COMPOSE_EXEC_APP        = $(COMPOSE_EXEC) app-dev
COMPOSE_RUN             = $(COMPOSE) run --rm
COMPOSE_RUN_APP         = $(COMPOSE_RUN) app-dev
COMPOSE_RUN_APP_NO_DEPS = $(COMPOSE_RUN) --no-deps app-dev 

COMPOSE_RUN_CROWDIN     = $(COMPOSE_RUN) crowdin crowdin

# -- Backend
MANAGE              	= $(COMPOSE_RUN_APP) python manage.py
MANAGE_EXEC         	= $(COMPOSE_EXEC_APP) python manage.py
MAIL_YARN           	= $(COMPOSE_RUN) -w /app/src/mail node yarn
PSQL_E2E 				= ./bin/postgres_e2e

# -- Frontend
PATH_FRONT          	= ./src/frontend
PATH_FRONT_DRIVE  		= $(PATH_FRONT)/apps/drive

# ==============================================================================
# RULES

default: help

data/media:
	@mkdir -p data/media

data/static:
	@mkdir -p data/static

# -- Project

create-env-local-files: ## create env.local files in env.d/development
create-env-local-files: 
	@touch env.d/development/crowdin.local
	@touch env.d/development/common.local
	@touch env.d/development/postgresql.local
	@touch env.d/development/kc_postgresql.local
.PHONY: create-env-local-files

create-docker-network: ## create the docker network if it doesn't exist
	@docker network create lasuite-network || true
.PHONY: create-docker-network

bootstrap: ## Prepare Docker images for the project
bootstrap: \
	data/media \
	data/static \
	create-env-local-files \
	build \
	migrate \
	back-i18n-compile \
	mails-install \
	mails-build \
	run
.PHONY: bootstrap

# -- Docker/compose
build: cache ?= --no-cache
build: ## build the project containers
	@$(MAKE) build-backend cache=$(cache)
	@$(MAKE) build-frontend cache=$(cache)
.PHONY: build

build-backend: cache ?=
build-backend: ## build the app-dev container
	@$(COMPOSE) build app-dev $(cache)
.PHONY: build-backend

build-frontend: cache ?=
build-frontend: ## build the frontend container
	@$(COMPOSE) build frontend-dev $(cache)
.PHONY: build-frontend-development

down: ## stop and remove containers, networks, images, and volumes
	@$(COMPOSE) down
	rm -rf data/postgresql.*
.PHONY: down

logs: ## display app-dev logs (follow mode)
	@$(COMPOSE) logs -f app-dev
.PHONY: logs

run-backend: ## start the backend container
	@$(MAKE) create-docker-network
	@$(COMPOSE) up --force-recreate -d celery-dev
	@$(COMPOSE) up --force-recreate -d nginx
	@$(MAKE) configure-wopi
.PHONY: run-backend

bootstrap-e2e: ## bootstrap the backend container for e2e tests, without frontend
bootstrap-e2e: \
	data/media \
	data/static \
	create-env-local-files \
	build-backend \
	back-i18n-compile \
	run-backend-e2e
.PHONY: bootstrap-e2e

clear-db-e2e: ## quickly clears the database for e2e tests, used in the e2e tests
	$(PSQL_E2E) -c "$$(cat bin/clear_db_e2e.sql)"
.PHONY: clear-db-e2e

run-backend-e2e: ## start the backend container for e2e tests, always remove the postgresql.e2e volume first
	@$(MAKE) stop
	rm -rf data/postgresql.e2e
	@ENV_OVERRIDE=e2e $(MAKE) run-backend
	@ENV_OVERRIDE=e2e $(MAKE) migrate
.PHONY: run-backend-e2e

run-tests-e2e: ## run the e2e tests, example: make run-tests-e2e -- --project chromium --headed
	@$(MAKE) run-backend-e2e	
	@args="$(filter-out $@,$(MAKECMDGOALS))" && \
	cd src/frontend/apps/e2e && yarn test $${args:-${1}}
.PHONY: run-tests-e2e

backend-exec-command: ## execute a command in the backend container
	@args="$(filter-out $@,$(MAKECMDGOALS))" && \
	$(MANAGE_EXEC) $${args}
.PHONY: backend-exec-command

run: ## start the development server and frontend development
run: 
	@$(MAKE) run-backend
	@$(COMPOSE) up --force-recreate -d frontend-dev
.PHONY: run

status: ## an alias for "docker compose ps"
	@$(COMPOSE) ps
.PHONY: status

stop: ## stop the development server using Docker
	@$(COMPOSE) stop
.PHONY: stop

# -- Backend

# Nota bene: Black should come after isort just in case they don't agree...
lint: ## lint back-end python sources
lint: \
  lint-ruff-format \
  lint-ruff-check \
  lint-pylint
.PHONY: lint

lint-ruff-format: ## format back-end python sources with ruff
	@echo 'lint:ruff-format started…'
	@$(COMPOSE_RUN_APP_NO_DEPS) ruff format .
.PHONY: lint-ruff-format

lint-ruff-check: ## lint back-end python sources with ruff
	@echo 'lint:ruff-check started…'
	@$(COMPOSE_RUN_APP_NO_DEPS) ruff check . --fix
.PHONY: lint-ruff-check

lint-pylint: ## lint back-end python sources with pylint only on changed files from main
	@echo 'lint:pylint started…'
	bin/pylint --diff-only=origin/main
.PHONY: lint-pylint

test: ## run project tests
	@$(MAKE) test-back-parallel
.PHONY: test

test-back: ## run back-end tests
	@args="$(filter-out $@,$(MAKECMDGOALS))" && \
	bin/pytest $${args:-${1}}
.PHONY: test-back

test-back-parallel: ## run all back-end tests in parallel
	@args="$(filter-out $@,$(MAKECMDGOALS))" && \
	bin/pytest -n auto $${args:-${1}}
.PHONY: test-back-parallel

makemigrations:  ## run django makemigrations for the drive project.
	@echo "$(BOLD)Running makemigrations$(RESET)"
	@$(COMPOSE) up -d postgresql
	@$(MANAGE) makemigrations
.PHONY: makemigrations

migrate:  ## run django migrations for the drive project.
	@echo "$(BOLD)Running migrations$(RESET)"
	@$(COMPOSE) up -d postgresql
	@$(MANAGE) migrate
.PHONY: migrate

superuser: ## Create an admin superuser with password "admin"
	@echo "$(BOLD)Creating a Django superuser$(RESET)"
	@$(MANAGE) createsuperuser --email admin@example.com --password admin
.PHONY: superuser

configure-wopi: ## configure the wopi settings
	@$(MANAGE) trigger_wopi_configuration
.PHONY: configure-wopi

back-i18n-compile: ## compile the gettext files
	@$(MANAGE) compilemessages --ignore=".venv/**/*"
.PHONY: back-i18n-compile

back-i18n-generate: ## create the .pot files used for i18n
	@$(MANAGE) makemessages -a --keep-pot --all
.PHONY: back-i18n-generate

shell: ## connect to django shell
	@$(MANAGE) shell #_plus
.PHONY: dbshell

# -- Database

dbshell: ## connect to database shell
	docker compose exec app-dev python manage.py dbshell
.PHONY: dbshell

resetdb: FLUSH_ARGS ?=
resetdb: ## flush database and create a superuser "admin"
	@echo "$(BOLD)Flush database$(RESET)"
	@$(MANAGE) flush $(FLUSH_ARGS)
	@${MAKE} superuser
.PHONY: resetdb

# -- Internationalization

crowdin-download: ## Download translated message from crowdin
	@$(COMPOSE_RUN_CROWDIN) download -c crowdin/config.yml
.PHONY: crowdin-download

crowdin-download-sources: ## Download sources from Crowdin
	@$(COMPOSE_RUN_CROWDIN) download sources -c crowdin/config.yml
.PHONY: crowdin-download-sources

crowdin-upload: ## Upload source translations to crowdin
	@$(COMPOSE_RUN_CROWDIN) upload sources -c crowdin/config.yml
.PHONY: crowdin-upload

i18n-compile: ## compile all translations
i18n-compile: \
	back-i18n-compile \
	frontend-i18n-compile
.PHONY: i18n-compile

i18n-generate: ## create the .pot files and extract frontend messages
i18n-generate: \
	back-i18n-generate \
	frontend-i18n-generate
.PHONY: i18n-generate

i18n-download-and-compile: ## download all translated messages and compile them to be used by all applications
i18n-download-and-compile: \
  crowdin-download \
  i18n-compile
.PHONY: i18n-download-and-compile

i18n-generate-and-upload: ## generate source translations for all applications and upload them to Crowdin
i18n-generate-and-upload: \
  i18n-generate \
  crowdin-upload
.PHONY: i18n-generate-and-upload

# -- Mail generator

mails-build: ## Convert mjml files to html and text
	@$(MAIL_YARN) build
.PHONY: mails-build

mails-build-html-to-plain-text: ## Convert html files to text
	@$(MAIL_YARN) build-html-to-plain-text
.PHONY: mails-build-html-to-plain-text

mails-build-mjml-to-html:	## Convert mjml files to html and text
	@$(MAIL_YARN) build-mjml-to-html
.PHONY: mails-build-mjml-to-html

mails-install: ## install the mail generator
	@$(MAIL_YARN) install
.PHONY: mails-install


# -- Misc
clean: ## restore repository state as it was freshly cloned
	git clean -idx
.PHONY: clean

clean-media: ## remove all media files
	rm -rf data/media/*
.PHONY: clean-media

help:
	@echo "$(BOLD)drive Makefile"
	@echo "Please use 'make $(BOLD)target$(RESET)' where $(BOLD)target$(RESET) is one of:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-30s$(RESET) %s\n", $$1, $$2}'
.PHONY: help

# Front
frontend-development-install: ## install the frontend locally
	cd $(PATH_FRONT_DRIVE) && yarn
.PHONY: frontend-development-install

frontend-lint: ## run the frontend linter
	cd $(PATH_FRONT) && yarn lint
.PHONY: frontend-lint

run-frontend-development: ## Run the frontend in development mode
	@$(COMPOSE) stop frontend-dev
	cd $(PATH_FRONT_DRIVE) && yarn dev
.PHONY: run-frontend-development

frontend-i18n-extract: ## Extract the frontend translation inside a json to be used for crowdin
	cd $(PATH_FRONT) && yarn i18n:extract
.PHONY: frontend-i18n-extract

frontend-i18n-generate: ## Generate the frontend json files used for crowdin
frontend-i18n-generate: \
	crowdin-download-sources \
	frontend-i18n-extract
.PHONY: frontend-i18n-generate

frontend-i18n-compile: ## Format the crowin json files used deploy to the apps
	cd $(PATH_FRONT) && yarn i18n:deploy
.PHONY: frontend-i18n-compile

# -- K8S
build-k8s-cluster: ## build the kubernetes cluster using kind
	./bin/start-kind.sh
.PHONY: build-k8s-cluster

start-tilt: ## start the kubernetes cluster using kind
	tilt up -f ./bin/Tiltfile
.PHONY: build-k8s-cluster
