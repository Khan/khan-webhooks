# khan-webhooks

## Deployment

First set up secrets.py by copying secrets.py.example to secrets.py,
and setting the phabricator_certificate field to be the value at
    https://phabricator.khanacademy.org/settings/71/panel/conduit/
(which should be the khan-webhoooks user).

Also fill in hipchat_token, taking the value from 'show secret' at
    https://phabricator.khanacademy.org/K39

Log into the App Engine console for the khan-webhooks app (as prod-deploy@), then open the Versions tab to see what the current version is. You can then deploy using

```
appcfg.py --oauth2 update . -V 9
```

where `9` is one more than the latest version. After `appcfg.py` finishes, go ahead and flip the version in the web interface to the one you just uploaded.
