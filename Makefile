.PHONY: help
help:
	@echo "Targets (e.g., 'make test'):"
	@echo
	@echo "   deps: initialize dependencies"
	@echo "   test: run some tests"
	@echo "   deploy: deploy to App Engine"

.PHONY: deps
deps:
	git submodule update --init --recursive

.PHONY: test
test: deps  # it's cheap enough to init submodules in this repo
	python pager_parrot_test.py

.PHONY: deploy
deploy: deps
	[ -s secrets.py ] || { echo "Set up secrets.py as per README.md"; exit 1; }
	gcloud preview app deploy app.yaml --project khan-webhooks --version 1 --promote
