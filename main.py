# TODO(colin): fix these lint errors (http://pep8.readthedocs.io/en/release-1.7.x/intro.html#error-codes)
# pep8-disable:E124,E128
import json
import logging
import re
import sys

import pager_parrot
import phabricator_fox
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


# Pagerduty adds a UUID to every message for deduping.  We do actually seem to
# get some messages twice, so we'll use it to dedupe; this is the list of
# message ids we've seen.  We'll just keep it in instance memory, because the
# dupes tend to be close together, and if we accidentally send to Slack twice
# it's not the end of the world.  In fact, Kamens thinks it's a very parrot-y
# thing to do.
pagerduty_ids_seen = set()


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
    'iOS': {'#mobile-1s-and-0s'},
    'android': {'#mobile-1s-and-0s'},
    'mobile': {'#mobile-1s-and-0s'},
    'mobile-client-webview-resources': {'#mobile-1s-and-0s'},
    'hivemind': {'#long-term-research'},
    'Cantor': {'#long-term-research'},
    'slacker-cow': {'#hipslack'},
    'jenkins-jobs': {'#hipslack'},
    'culture-cow': {'#hipslack'},
    'khan-webhooks': {'#hipslack'},

    # Content tools repositories
    'content-tools-tools': {'#content-tools'},
    'graphie-to-png': {'#content-tools'},
    'KAS': {'#content-tools'},
    'KaTeX': {'#content-tools'},
    'khan-exercises': {'#content-tools'},
    'mathquill': {'#content-tools'},
    'perseus': {'#content-tools', '#mobile-1s-and-0s'},
    'perseus-one': {'#content-tools'},
    'react-native-shared': {'#mobile-1s-and-0s'},
    'RCSS': {'#content-tools'},
    'react-components': {'#content-tools'},
    'simple-markdown': {'#content-tools'},
    'kmath': {'#content-tools'},
}


USER_CHANNEL_MAP = {
    'abdulrahman': {'#il-eng'},
    'alice': {'#classroom-eng'},
    'ann': {'#classroom-eng'},
    'aric': {'#classroom-eng', '#reports-eng'},
    'briangenisio': {'#il-eng'},
    'bryan': {'#il-eng'},
    'boris': {'#reports-eng'},
    'cora': {'#il-eng', '#reports-eng'},
    'dhruv': {'#classroom-eng', '#reports-eng'},
    'diedra': {'#il-eng'},
    'erik': {'#classroom-eng'},
    'hannah': {'#classroom-eng'},
    'jared': {'#il-eng'},
    'jangmi': {'#classroom-eng'},
    'kairui': {'#il-eng'},
    'kevinb': {'#il-eng'},
    'kphilip': {'#reports-eng'},
    'miguel': {'#classroom-eng'},
    'mita': {'#classroom-eng'},
    'nrowe': {'#il-eng'},
    'samuel': {'#classroom-eng'},
    'sean': {'#classroom-eng', '#reports-eng'},
    'yash': {'#classroom-eng'},
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


def _send_to_slack(message, channel, username, icon_emoji):
    logging.info('Posting "%s" to %s in Slack' % (message, channel))
    post_data = {
        'text': message,
        'channel': channel,
        'username': username,
        'icon_emoji': icon_emoji,
        'link_names': 1,
    }
    requests.post(secrets.slack_webhook_url,
                  data={'payload': json.dumps(post_data)})


def _build_slack_message(phid_info, transaction_type, author_phid):
    # `transaction_type` refers to the type of change that occurred.
    # Some common examples include: `comment`, `update`, `title`.
    # However, we are only concerned with `create` and `abandon`
    uri = phid_info['uri']
    description = phid_info['fullName'].split(': ', 1)[-1]
    diff_id = phid_info['name']
    message = u':phabricator: <%s|%s>: %s (%s by %s)' % (
        uri, diff_id, description, transaction_type, author_phid)
    return message


class PhabricatorFox(webapp2.RequestHandler):
    """Handler that is run when `new-phabricator-feed` is triggered.

    Following the deprecation of the feed.http-hooks, this handler
    follows the Phabricator system documented at
    https://secure.phabricator.com/book/phabricator/article/webhooks/
    """
    def post(self):
        logging.info("Processing %s" % self.request.body)
        phid = self.request.body['object']['phid']
        phid_map = {
            'phids': [t['phid'] for t in self.request['transactions']]
        }
        phab = _get_phabricator()
        resp = phab.phid.transaction.search(
            objectIdentifier=phid, constraints=phid_map).response
        if resp:
            data = resp['data']
            for transaction in data:
                trans_type = transaction.get('type')
                if trans_type not in ['create', 'abandon']:
                    logging.info(
                        "Transaction %s not a match. Skipping!" % trans_type)
                    continue
                author_phid = transaction['authorPHID']
                logging.info("Transaction type: %s" % (trans_type))
                phid_query = phab.phid.phid.query(phids=[phid]).response
                # Since we're only passing in 1 phid, there should only be
                # one (key, value) pair returned. We are only interested
                # in the value.
                if not phid_query:
                    logging.info("No info found for %s" % (phid))
                    continue
                phid_info = phid_query.values()[0]
                message = _build_slack_message(
                    phid_info, trans_type, author_phid)
                # If phid_info['name'] returns D123, 123 is the
                # repository PHID, so we remove the first
                # character
                repo_phid = _repository_phid_from_diff_id(
                    int(phid_info['name'].lstrip('D')))
                repo_callsign = None
                if repo_phid:
                    repo_callsign = _callsign_from_repository_phid(repo_phid)
                    if not repo_callsign:
                        logging.info(
                            "Unable to get repo callsign for %s" % repo_phid)

                _send_to_slack(
                    message, '#bot-testing', 'Phabricator Fox', ':fox:')
                extra_channels = set()
                for channel in CALLSIGN_CHANNEL_MAP.get(repo_callsign, []):
                    extra_channels.add(channel)

                for channel in USER_CHANNEL_MAP.get(author, []):
                    extra_channels.add(channel)

                # TODO(cathy): Uncomment this part after verifying
                # message is correct for channel in extra_channels:
                #     _send_to_slack(
                #         message, channel, 'Phabricator Fox', ':fox:')
        else:
            logging.info("No response found for this phid: %s" % (phid))

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('OK')


# Add me to feed.http-hooks in Phabricator config
class PhabFox(webapp2.RequestHandler):
    def post(self):
        logging.info("Processing %s" % self.request.arguments())
        if (self.request.get('storyType') ==
                'PhabricatorApplicationTransactionFeedStory'):
            match = re.match(
                phabricator_fox.MESSAGE_RX,
                self.request.get('storyText'))

            if match:
                url = "%s/%s" % (secrets.phabricator_host, match.group('code'))
                author = match.group('who')
                message = u':phabricator: <%s|%s>: %s (%s by %s)' % (
                    url, match.group('code'),
                    match.group('description'),
                    match.group('action'), author)

                repo_phid = _repository_phid_from_diff_id(
                    int(match.group('code')[1:]))
                repo_callsign = None
                if repo_phid:
                    repo_callsign = _callsign_from_repository_phid(repo_phid)
                    if not repo_callsign:
                        logging.info(
                                "Unable to determine repo callsign for %s" %
                                repo_phid)

                _send_to_slack(
                    message, '#1s-and-0s-commits', 'Phabricator Fox', ':fox:')

                extra_channels = set()
                for channel in CALLSIGN_CHANNEL_MAP.get(repo_callsign, []):
                    extra_channels.add(channel)

                for channel in USER_CHANNEL_MAP.get(author, []):
                    extra_channels.add(channel)

                for channel in extra_channels:
                    _send_to_slack(
                            message, channel, 'Phabricator Fox', ':fox:')
            else:
                logging.info("Story text didn't match regexp. Text was: %s" %
                        self.request.get('storyText'))
        else:
            logging.info("Ignoring unknown story type: %s" %
                    self.request.get('storyType'))

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('OK')


# Add me as an outgoing webhook for a service in PagerDuty.
# See http://911.khanacademy.org/ for details.
class PagerParrot(webapp2.RequestHandler):
    # TODO(benkraft): this has no auth whatsoever.  I'm not too worried about
    # it, but we might want to do some sort of checking (e.g. via hitting the
    # PagerDuty API) or use an obscure URL.
    def post(self):
        logging.info("Processing %s" % self.request.body)
        payload = json.loads(self.request.body)

        global pagerduty_ids_seen
        for message in payload['messages']:
            if (message['id'] not in pagerduty_ids_seen and
                    message['type'] == 'incident.trigger'
                    ):
                should_ping = pager_parrot.consider_ping()
                # Only trigger if we haven't seen the message, and if it's a
                # trigger, rather than an acknowledgement or resolve.
                for channel in pager_parrot.CHANNELS:
                    _send_to_slack(
                        pager_parrot.format_message(
                            message['data']['incident'], channel,
                            should_ping=should_ping),
                        channel, 'Pager Parrot', ':parrot:')
                pagerduty_ids_seen.add(message['id'])


app = webapp2.WSGIApplication([
    ('/new-phabricator-feed', PhabricatorFox),
    ('/phabricator-feed', PhabFox),
    ('/pagerduty-feed', PagerParrot),
])
