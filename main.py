import json
import logging
import re
import sys

import webapp2

try:
    import secrets
except ImportError:
    print ("secrets.py is missing -- copy and tweak the template from "
           "secrets.py.example.")
    raise

sys.path.insert(1, 'third_party')
from third_party import phabricator
from third_party import requests


def _get_phabricator():
    return phabricator.Phabricator(
        host=secrets.phabricator_host + '/api/',
        username=secrets.phabricator_username,
        certificate=secrets.phabricator_certificate,
    )


def _callsigns_from_repo_urls(repo_urls):
    """Given a list of possible repo URLs, return a set of all callsigns that
    correspond to them.

    Example:
        _callsigns_from_repo_urls(["git@github.com:Khan/webapp"])  # ["GWA"]
    """
    phab = _get_phabricator()
    # (This returns repos for URLs that match and ignores ones that don't.)
    resp = phab.phid.repository.query(remoteURIs=repo_urls).response
    return set(repo['callsign'] for repo in resp)


# The following is a list of Khan GitHub repositories to interested Slack
# channels. These channels will be notified, in addition to #1s-and-0s,
# when interesting activity happens. You do not need the initial "Khan/".
GITHUB_CHANNEL_MAP = {
    'iOS': {'#mobile'},
    'android': {'#mobile'},
    'mobile-client-webview-resources': {'#mobile'},
    'Early-Math-Prototypes': {'#early-math'},
    'slacker-cow': {'#hipslack'},
    'jenkins-tools': {'#hipslack'},
    'culture-cow': {'#hipslack'},
    'khan-webhooks': {'#hipslack'},

    # Content tools repositories
    'content-tools-tools': {'#content-tools'},
    'graphie-to-png': {'#content-tools'},
    'KAS': {'#content-tools'},
    'KaTeX': {'#content-tools'},
    'khan-exercises': {'#content-tools'},
    'mathquill': {'#content-tools'},
    'perseus': {'#content-tools'},
    'perseus-one': {'#content-tools'},
    'RCSS': {'#content-tools'},
    'react-components': {'#content-tools'},
    'simple-markdown': {'#content-tools'},
    'kmath': {'#content-tools'},
}


# Phabricator only gives us callsigns, so map these once and be done with it.
CALLSIGN_CHANNEL_MAP = {}


# Use my favorite old scary Python hack to make this a run-one initializer
def _initialize_callsign_map(initialized=[False]):
    if not initialized[0]:
        initialized[0] = True
        for repo, channels in GITHUB_CHANNEL_MAP.viewitems():
            for callsign in _callsigns_from_repo_urls(
                    ['git@github.com:Khan/%s' % repo]):
                CALLSIGN_CHANNEL_MAP[callsign] = channels

        # Need the extra parens on this next line, or you'll get just the key
        logging.info('Channel map: %r' % (CALLSIGN_CHANNEL_MAP,))


_initialize_callsign_map()


def _repository_phid_from_diff_id(diff_id):
    phab = _get_phabricator()
    resp = phab.phid.differential.query(ids=[diff_id]).response
    if resp:
        return resp[0]['repositoryPHID']


def _callsign_from_repository_phid(phid):
    """Given a repository's PHID, return its callsign. Returns None if the
    repository can't be found.

    Example:
        # Returns "GI"
        _callsign_from_repository_phid("PHID-REPO-izgobria5djkn7tadrmf")
    """
    phab = _get_phabricator()
    resp = phab.phid.repository.query(phids=[phid]).response
    if resp:
        return resp[0]['callsign']


def _send_to_slack(message, channel):
    logging.info('Posting "%s" to %s in Slack' % (message, channel))
    post_data = {
        'text': message,
        'channel': channel,
        'username': 'Phabricator Fox',
        'icon_emoji': ':fox:',
    }
    requests.post(secrets.slack_webhook_url,
                  data={'payload': json.dumps(post_data)})


# Add me to feed.http-hooks in Phabricator config
class PhabFox(webapp2.RequestHandler):
    def post(self):
        logging.info("Processing %s" % self.request.arguments())
        if (self.request.get('storyType') ==
                'PhabricatorApplicationTransactionFeedStory'):
            match = re.match(
                r"^([a-zA-Z0-9.]+ (?:created|abandoned) )"
                r"(D([0-9]+): .*)\.$",
                self.request.get('storyText'))

            if match:
                # ('alpert created ', 'D1234: Moo', '1234')
                subject_verb, link_text, diff_id = match.groups()
                diff_id = int(diff_id)

                url = "%s/D%s" % (secrets.phabricator_host, diff_id)
                message = "%s :phabricator: <%s|%s>." % (subject_verb,
                                                         url, link_text)

                repo_phid = _repository_phid_from_diff_id(diff_id)
                repo_callsign = None
                if repo_phid:
                    repo_callsign = _callsign_from_repository_phid(repo_phid)

                _send_to_slack(message, '#1s-and-0s')
                for extra_channel in CALLSIGN_CHANNEL_MAP.get(
                        repo_callsign, []):
                    _send_to_slack(message, extra_channel)

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('OK')

app = webapp2.WSGIApplication([
    ('/phabricator-feed', PhabFox),
])
