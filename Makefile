GOOGLE_SDK_ROOT=$(HOME)/google-cloud-sdk/

.PHONY: help
help:
	@echo "Targets (e.g., 'make test'):"
	@echo
	@echo "   deps: initialize dependencies"
	@echo "   check: run some tests"
	@echo "   test: run some tests (alias for 'check')"
	@echo "   deploy: deploy to App Engine"

.PHONY: deps
deps:
	git submodule update --init --recursive

.PHONY: check test
check test: deps  # it's cheap enough to init submodules in this repo
	python runner.py $(GOOGLE_SDK_ROOT)

secrets.py: secrets-config.json
	./generate_secrets.py

.PHONY: deploy
deploy: deps secrets.py
	gcloud app deploy app.yaml --project khan-webhooks --version 1 --promote
