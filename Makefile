.PHONY: help
help:
	@echo "Targets (e.g., 'make test'):"
	@echo
	@echo "   test: run some tests"
	@echo "   deploy: deploy to App Engine"

.PHONY: test
test:
	python pager_parrot_test.py

.PHONY: deploy
deploy:
	[ -s secrets.py ] || { echo "Set up secrets.py as per README.md"; exit 1; }
	gcloud preview app deploy app.yaml --project khan-webhooks --version 1 --promote
