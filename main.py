import cgi
import logging
import re
import sys

try:
    import secrets
except ImportError:
    print ("secrets.py is missing -- copy and tweak the template from "
            "secrets.py.example.")
    raise

sys.path.insert(1, 'third_party')
from third_party.flask import Flask
from third_party.flask import request
from third_party import phabricator
from third_party import requests

app = Flask(__name__)


def username_from_phid(phid):
    phab = phabricator.Phabricator(
            host=secrets.phabricator_host + '/api/',
            username=secrets.phabricator_username,
            certificate=secrets.phabricator_certificate,
        )
    resp = phab.phid.lookup(names=[phid]).response
    if phid in resp:
        return resp[phid]['name']


# Add me to feed.http-hooks in Phabricator config
@app.route('/phabricator-feed', methods=['POST'])
def hello():
    logging.info("Processing %s" % request.form)
    # TODO(alpert): Consider using native Phabricator Jabber support
    # https://secure.phabricator.com/T1271 when it happens.
    if (request.form['storyType'] ==
            'PhabricatorApplicationTransactionFeedStory'):
        def linkify(match):
            url = "%s/%s" % (secrets.phabricator_host, match.group(3))
            return """%(pre)s<a href="%(url_html)s">%(link_html)s</a>.""" % {
                    'pre': match.group(1),
                    'url_html': cgi.escape(url, True),
                    'link_html': cgi.escape(match.group(2), True),
                }

        message, replaced = re.subn(
            r"^([a-zA-Z0-9.]+ (?:created|abandoned) )"
            r"((D[0-9]+): .*)\.$",
            linkify,
            request.form['storyText'])

        if replaced:
            resp = requests.post(
                "https://api.hipchat.com/v1/rooms/message?auth_token=%s" %
                    secrets.hipchat_token,
                data={
                    'from': 'Phabricator Fox',
                    # TODO(alpert): Different rooms for different repos?
                    'room_id': '1s and 0s',
                    'color': 'yellow',
                    'message_format': 'html',
                    'message': message
                })
            print resp.text

    return ''

if __name__ == '__main__':
    app.run(debug=True)
