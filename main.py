import cgi
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
    # TODO(alpert): Consider using native Phabricator Jabber support
    # https://secure.phabricator.com/T1271 when it happens.
    if request.form['storyType'] == 'PhabricatorFeedStoryDifferential':
        action = request.form['storyData[action]']
        sentence_html_dict = {
            'create':
                """%(name_html)s created revision """
                """<a href="%(url_html)s">%(link_html)s</a>""",
            'commit':
                """%(name_html)s closed revision """
                """<a href="%(url_html)s">%(link_html)s</a>""",
            'abandon':
                """%(name_html)s abandoned revision """
                """<a href="%(url_html)s">%(link_html)s</a>""",
        }
        sentence_html = sentence_html_dict.get(action)
        if sentence_html is not None:
            phid = request.form['storyData[actor_phid]']
            print phid
            name = username_from_phid(phid)

            rev_id = request.form['storyData[revision_id]']
            url = "%s/D%s" % (secrets.phabricator_host, rev_id)

            title = request.form['storyData[revision_name]']
            link = "D%s: %s" % (rev_id, title)

            message = sentence_html % {
                    'name_html': cgi.escape(name, True),
                    'url_html': cgi.escape(url, True),
                    'link_html': cgi.escape(link, True),
                }

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
