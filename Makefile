PYTHON = .venv/bin/python
PYTEST = .venv/bin/pytest
CELERY = .venv/bin/celery
PRECOMMIT = .venv/bin/pre-commit

.PHONY: run migrations show-migrations migrate collectstatic \
        makemessages compilemessages bot celery-worker \
        build watch test lint

run:
	$(PYTHON) manage.py runserver

migrations:
	$(PYTHON) manage.py makemigrations

show-migrations:
	$(PYTHON) manage.py showmigrations

migrate:
	$(PYTHON) manage.py migrate

collectstatic:
	$(PYTHON) manage.py collectstatic --noinput

makemessages:
	$(PYTHON) manage.py makemessages -l mn --ignore .venv

compilemessages:
	$(PYTHON) manage.py compilemessages

bot:
	$(PYTHON) manage.py run_bot --drop-pending

celery-worker:
	$(CELERY) -A config worker -l INFO

build:
	npm run build

watch:
	npm run watch

test:
	$(PYTEST)

lint:
	$(PRECOMMIT) run --all-files
