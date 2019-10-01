# khan-webhooks

## Deployment

First ensure that you have access to the right set of secrets by running `make
secrets.py`. You will need to first set up access to the keeper cli using the
directions [here](http://khanacademy.org/r/keeper-cli).

You can then deploy by running `make deploy`.

You can view the logs at https://console.cloud.google.com/logs/viewer?project=khan-webhooks
