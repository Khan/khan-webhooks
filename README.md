# khan-webhooks

## Deployment

First, copy khan-webhooks-secrets.py from Dropbox into secrets.py in this directory.

Log into the App Engine console for the khan-webhooks app (as prod-deploy), then open the Versions tab to see what the current version is. You can then deploy using

```
appcfg.py --oauth2 update . -V 9
```

where `9` is one more than the latest version. After `appcfg.py` finishes, go ahead and flip the version in the web interface to the one you just uploaded.
