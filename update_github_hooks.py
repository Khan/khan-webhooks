"""Update hooks on all our GitHub repos to point to our khan-webhooks endpoint,
removing existing HipChat hooks if they exist. You'll want to be an owner of
the organization on GitHub or you'll probably receive various 401 errors while
running the script.
"""
import argparse
import getpass
import json

import requests


def org_repos(org_name, github_auth):
    """Generator for all GitHub repo JSON objects for an organization."""
    url = "https://api.github.com/orgs/%s/repos" % org_name
    while url:
        r = requests.get(url, auth=github_auth)

        for repo in r.json():
            yield repo

        # Next page...
        url = r.links.get('next', {'url': None})['url']


def update_hooks(repo_name, github_auth, dry_run):
    """Given a repo name in the form 'Khan/webapp', ensure that all HipChat
    hooks have been deleted and that there exists a khan-webhooks web hook.
    """
    print repo_name

    r = requests.get("https://api.github.com/repos/%s/hooks" % repo_name,
                     auth=github_auth)
    hooks = r.json()

    hipchat_hooks = []
    khan_webhooks_hook = None

    for hook in hooks:
        if hook['name'] == 'hipchat':
            hipchat_hooks.append(hook)
        elif hook['name'] == 'web' and (hook['config']['url'] ==
                'https://khan-webhooks.appspot.com/github-feed'):
            khan_webhooks_hook = hook

    for hook in hipchat_hooks:
        if hook['active']:
            print "-- Deleting HipChat hook (%s)" % hook['id']
        else:
            print "-- Deleting inactive HipChat hook (%s)" % hook['id']
        if not dry_run:
            requests.delete("https://api.github.com/repos/%s/hooks/%s" %
                                (repo_name, hook['id']),
                            auth=github_auth)

    if khan_webhooks_hook:
        if khan_webhooks_hook['active']:
            print "-- Web hook already present"
        else:
            print "-- Web hook present but inactive"
    else:
        print "-- Creating web hook"
        if not dry_run:
            r = requests.post(
                "https://api.github.com/repos/%s/hooks" % id,
                data=json.dumps({
                    'name': 'web',
                    'config': {
                        'content_type': 'json',
                        'url': 'https://khan-webhooks.appspot.com/github-feed',
                    },
                    'events': ['push'],
                    'active': True,
                }), auth=github_auth)


def main(dry_run):
    print "GitHub username:",
    github_username = raw_input()
    github_password = getpass.getpass(
        "Password (or personal auth token) for %s: " % github_username)
    github_auth = (github_username, github_password)

    for repo in org_repos('Khan', github_auth):
        # e.g., 'Khan/webapp'
        repo_name = repo['owner']['login'] + '/' + repo['name']
        update_hooks(repo_name, github_auth, dry_run)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', '-n', action='store_true',
            help="Skip all writes to GitHub")
    args = parser.parse_args()

    main(args.dry_run)
