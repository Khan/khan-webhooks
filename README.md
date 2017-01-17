# khan-webhooks

## Deployment

First set up secrets.py by copying secrets.py.example to secrets.py,
and setting the phabricator_certificate field to be the value from
'show secret' at
    https://phabricator.khanacademy.org/K56

Also fill in slack_webhook_url, taking the value from 'show secret' at
    https://phabricator.khanacademy.org/K94

You can then deploy by running `make deploy`.

You can view the logs at https://console.cloud.google.com/logs/viewer?project=khan-webhooks
