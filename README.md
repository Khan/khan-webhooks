# khan-webhooks

## Deployment

First set up secrets.py by copying secrets.py.example to secrets.py,
and setting the phabricator_certificate field to be the value from
the Keeper secret at Devops > "Phabricator certificate for khan-webhooks"

Also fill in slack_bot_access_token, taking the value from the Keeper secret at
Devops > Slack > "Slack: Bot token (for API) for Pager Parrot"

You can then deploy by running `make deploy`.

You can view the logs at https://console.cloud.google.com/logs/viewer?project=khan-webhooks
