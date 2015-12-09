# khan-webhooks

## Deployment

First set up secrets.py by copying secrets.py.example to secrets.py,
and setting the phabricator_certificate field to be the value from
'show secret' at
    https://phabricator.khanacademy.org/K56

Also fill in slack_webhook_url, taking the value from 'show secret' at
    https://phabricator.khanacademy.org/K94

Then open the Versions tab to see what the current version is.
You can then deploy using

```
appcfg.py . -V 9
```

where `9` is one more than the latest version.
After `appcfg.py` finishes, go ahead and flip the version in the
web interface to the one you just uploaded.
