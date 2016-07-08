deploy:
	[ -s secrets.py ] || { echo "Set up secrets.py as per README.md"; exit 1; }
	gcloud preview app deploy app.yaml --project khan-webhooks --version 1 --promote
