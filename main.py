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


def _get_phabricator():
    return phabricator.Phabricator(
            host=secrets.phabricator_host + '/api/',
            username=secrets.phabricator_username,
            certificate=secrets.phabricator_certificate,
        )


def _username_from_phid(phid):
    phab = _get_phabricator()
    resp = phab.phid.lookup(names=[phid]).response
    if phid in resp:
        return resp[phid]['name']


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


def _callsigns_from_short_repo_names(short_repo_names):
    """Given a list of short repo names, like 'Khan/webapp', return a set of
    all callsigns that correspond to them

    Example:
        _callsigns_from_short_repo_names(["Khan/webapp"])  # ["GWA"]
    """
    results = []
    for short_repo_name in short_repo_names:
        # GitHub repos take one of these two forms in Phabricator depending on
        # whether they're public or private
        urls = (
            "https://github.com/%s" % short_repo_name,
            "git@github.com:%s" % short_repo_name
        )
        for callsign in _callsigns_from_repo_urls(urls):
            results.append(callsign)
    return results


CONTENT_TOOLS_REPOS = [
    'Khan/content-tools-tools',
    'Khan/graphie-to-png',
    'Khan/KAS',
    'Khan/KaTeX',
    'Khan/khan-exercises',
    'Khan/mathquill',
    'Khan/perseus',
    'Khan/perseus-one',
    'Khan/RCSS',
    'Khan/react-components'
]

_CONTENT_TOOLS_CALLSIGNS_CACHE = None


def _get_content_tools_callsigns():
    global _CONTENT_TOOLS_CALLSIGNS_CACHE
    if _CONTENT_TOOLS_CALLSIGNS_CACHE is None:
        _CONTENT_TOOLS_CALLSIGNS_CACHE = (
                _callsigns_from_short_repo_names(CONTENT_TOOLS_REPOS))
    return _CONTENT_TOOLS_CALLSIGNS_CACHE


def _looksoon(callsigns):
    """Tell Phabricator to pull the repos with specified callsigns soon."""
    phab = _get_phabricator()
    phab.phid.diffusion.looksoon(callsigns=list(callsigns))


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


def _link_html(url, text):
    return '<a href="%s">%s</a>' % (cgi.escape(url, True), cgi.escape(text))


def _send_to_hipchat(message, room, from_name, color='yellow'):
    resp = requests.post(
        "https://api.hipchat.com/v1/rooms/message?auth_token=%s" %
            secrets.hipchat_token,
        data={
            'from': from_name,
            'room_id': room,
            'color': color,
            'message_format': 'html',
            'message': message
        })
    logging.info("Sent to HipChat: %s", resp.text)


# Add me to feed.http-hooks in Phabricator config
@app.route('/phabricator-feed', methods=['POST'])
def phabricator_feed():
    logging.info("Processing %s" % request.form)
    if (request.form['storyType'] ==
            'PhabricatorApplicationTransactionFeedStory'):
        match = re.match(
            r"^([a-zA-Z0-9.]+ (?:created|abandoned) )"
            r"(D([0-9]+): .*)\.$",
            request.form['storyText'])

        if match:
            # ('alpert created ', 'D1234: Moo', '1234')
            subject_verb, link_text, diff_id = match.groups()
            diff_id = int(diff_id)

            url = "%s/D%s" % (secrets.phabricator_host, diff_id)
            message = "%s%s." % (subject_verb, _link_html(url, link_text))

            repo_phid = _repository_phid_from_diff_id(diff_id)
            repo_callsign = None
            if repo_phid:
                repo_callsign = _callsign_from_repository_phid(repo_phid)

            _send_to_hipchat(message, '1s and 0s', 'Phabricator Fox')
            if repo_callsign == 'GI':
                _send_to_hipchat(message, 'Mobile!', 'Phabricator Fox')
            if repo_callsign in _get_content_tools_callsigns():
                _send_to_hipchat(message, 'Content tools', 'Phabricator Fox')

    return ''


# Add me as a GitHub web hook
@app.route('/github-feed', methods=['POST'])
def github_feed():
    event_type = request.headers.get('X-GitHub-Event')
    # payload looks like https://gist.github.com/spicyj/6c9c13af85771f4fcd39
    payload = request.json
    logging.info("Processing %s: %s", event_type, payload)
    if event_type != 'push':
        logging.info("Skipping event type %s", event_type)
        return ''

    if not payload['ref'].startswith('refs/heads/'):
        logging.info("Skipping ref %s", payload['ref'])
        return ''

    branch = payload['ref'][len('refs/heads/'):]
    # Like "Khan/webapp"
    short_repo_name = "%s/%s" % (payload['repository']['owner']['name'],
                                 payload['repository']['name'])

    old_commits = [c for c in payload['commits'] if not c['distinct']]
    new_commits = [c for c in payload['commits'] if c['distinct']]

    branch_link_html = _link_html(
        "%s/tree/%s" % (payload['repository']['url'], branch), branch)
    repo_html = _link_html(payload['repository']['url'], short_repo_name)
    before_html = _link_html(
        "%s/commit/%s" % (payload['repository']['url'], payload['before']),
        payload['before'][:7])
    after_html = _link_html(
        "%s/commit/%s" % (payload['repository']['url'], payload['after']),
        payload['after'][:7])

    if payload['created']:
        verb_html = "created branch %s of %s" % (branch_link_html, repo_html)
    elif payload['deleted']:
        verb_html = "deleted branch %s of %s" % (
            cgi.escape(branch, True), repo_html)
    elif payload['forced']:
        verb_html = "force-pushed branch %s of %s from %s to %s" % (
            branch_link_html, repo_html, before_html, after_html)
    elif new_commits:
        verb_html = "pushed to branch %s of %s" % (branch_link_html, repo_html)
    else:
        verb_html = "fast-forward pushed branch %s of %s to %s" % (
            branch_link_html, repo_html, after_html)

    username = payload['pusher']['name']
    username_link_html = _link_html(
        "https://github.com/%s" % username, username)

    html_lines = []
    html_lines.append("%s %s" % (username_link_html, verb_html))

    COMMITS_TO_SHOW = 5

    for commit in new_commits[:COMMITS_TO_SHOW]:
        MAX_LINE_LENGTH = 60
        commit_message = commit['message']
        if '\n' in commit_message:
            commit_message = commit_message[:commit_message.index('\n')]
        if len(commit_message) > MAX_LINE_LENGTH:
            commit_message = commit_message[:MAX_LINE_LENGTH - 3] + '...'

        commit_link = _link_html(commit['url'], commit['id'][:7])

        revision_link = None
        match = re.search(
            r'\n\nDifferential Revision: (http.+/(D[0-9]+))(?:\n\n|$)',
            commit['message'])
        if match:
            revision_link = _link_html(match.group(1), match.group(2))

        html_lines.append("- %s (%s%s)" % (
            cgi.escape(commit_message, True),
            revision_link + ', ' if revision_link else '',
            commit_link))

    if old_commits:
        # If this is a fast-forward push, omit the "and"
        and_text = "and " if new_commits else ""
        if len(old_commits) == 1:
            html_lines.append("- %s1 existing commit" % and_text)
        else:
            html_lines.append("- %s%s existing commits" %
                              (and_text, len(old_commits)))

    if len(new_commits) > COMMITS_TO_SHOW:
        html_lines.append("- and %s more..." %
                          (len(new_commits) - COMMITS_TO_SHOW))

    message_html = '<br>'.join(html_lines)

    # TODO(alpert): More elaborate configuration? We'll see if this gets
    # unmanageable.
    _send_to_hipchat(message_html, '1s/0s: commits', 'GitHub')
    if short_repo_name == 'Khan/webapp' and (
            (branch + '-').startswith('athena-')):
        _send_to_hipchat(message_html, 'Athena', 'GitHub')
    if short_repo_name == 'Khan/webapp' and branch == 'cnc':
        _send_to_hipchat(message_html, 'Classy coaches', 'GitHub')
    if short_repo_name == 'Khan/webapp' and (
            (branch + '-').startswith('sat-')):
        _send_to_hipchat(message_html, 'SAT', 'GitHub')
    if short_repo_name == 'Khan/webapp' and (
            (branch + '-').startswith('growth-')):
        _send_to_hipchat(message_html, 'Growth', 'GitHub')
    if short_repo_name == 'Khan/iOS':
        _send_to_hipchat(message_html, 'Mobile!', 'GitHub')
    if short_repo_name in CONTENT_TOOLS_REPOS:
        _send_to_hipchat(message_html, 'Content tools', 'GitHub')

    if (short_repo_name == 'Khan/webapp' and branch == 'master' and
            username != 'ka-role'):
        _send_to_hipchat(
            "^^ Illegal push to master branch of Khan/webapp. %s, run "
            "tools/hook-check.sh to set up hooks to prevent accidental "
            "pushes to master in the future." % cgi.escape(username, True),
            '1s/0s: commits', 'GitHub', color='red')

    # Let's tell Phabricator to pull the repo we just got a notification about.
    # `callsigns` is a list like ["GWA"] or [].
    callsigns = _callsigns_from_short_repo_names([short_repo_name])
    if callsigns:
        _looksoon(callsigns)

    return ''

if __name__ == '__main__':
    app.run(debug=True)
