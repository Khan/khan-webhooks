"""Pure utilities and configuration settings for Pager Parrot."""
import collections
import datetime
import textwrap

# A configuration object describing how a slack channel should respond to an
# incident. The high-priority action will be taken for P911 incidents. The
# medium-priority action will be taken for non-P911 incidents on weekdays. The
# low-priority action will be taken for non-P911 incidents on weekends. See
# below for the possible values of these fields.
Configuration = collections.namedtuple('Configuration',
                                       ('channel_type',
                                        'high_priority_action',
                                        'medium_priority_action',
                                        'low_priority_action',
                                        ))

# Values for channel_type.
# Different types of channels: what kind of message do we deliver?
_FIRST_PARTY = 'ChannelType[_FIRST_PARTY]'
_THIRD_PARTY = 'ChannelType[_THIRD_PARTY]'


# Globals and constants for consider_ping
_last_ping = datetime.datetime.min
_last_message = datetime.datetime.min
_PING_AFTER_MESSAGE_TIMEOUT = datetime.timedelta(minutes=30)
_PING_AFTER_PING_TIMEOUT = datetime.timedelta(hours=3)


def consider_ping():
    """Consider whether to @channel for a Pager Parrot message now.

    If there are a bunch of distinct alerts in a short period of time,
    we deduplicate those, and only @channel on the first one "recently".

    This function updates the times we last did an @channel, and the times we
    last sent a message, and returns True if we should do an @channel this
    time.  If you call this, you promise to @channel if it tells you so.

    We'll skip the @channel if there's been a message in the
    last 30 minutes, and an @channel in the last 3 hours.  We do it this way so
    that a long-running incident that alerts every 10 minutes won't result in a
    bunch of @channels, but an incident that is resolved, and then recurs a few
    hours later, will.

    Like main.pagerduty_ids_seen, we just keep this in instance memory, because
    a false positive occasionally is way better than Pager Parrot crashing
    because it can't talk to the datastore.
    """
    global _last_ping
    global _last_message
    now = datetime.datetime.now()

    will_ping = not (
        # Skip a ping if our last message *and* last ping were recent.
        now - _last_message < _PING_AFTER_MESSAGE_TIMEOUT and
        now - _last_ping < _PING_AFTER_PING_TIMEOUT)

    _last_message = now
    if will_ping:
        _last_ping = now

    return will_ping


def _preprocess_base_message(msg):
    """Dedent and collapse newlines."""
    return ' '.join(textwrap.dedent(msg).strip().split('\n'))


_BASE_MESSAGES = {
    _FIRST_PARTY: _preprocess_base_message(
        """\
        {at_mention}Oh no! {priority} <{url}|incident #{number}> opened
        in PagerDuty: {summary}. I'll {next_steps} to make sure someone is
        looking at it. See <http://911.khanacademy.org/|the 911 docs> for more
        information on these alerts.
        """),
    _THIRD_PARTY: _preprocess_base_message(
        """\
        {at_mention}{priority} <incident #{number}> opened in PagerDuty:
        {summary}. The KA dev team has been alerted.
        """),
}


# Values for {high,medium,low}_priority_action.
# Different verbosities for the parrot: whom do we ping?
_PING_WITH_AT_CHANNEL = 'Action[_PING_WITH_AT_CHANNEL]'
_PING_WITH_AT_HERE = 'Action[_PING_WITH_AT_HERE]'
_SUPPRESS_PING = 'Action[_SUPPRESS_PING]'

# Map from action to (at-mention, next steps)
_ACTIONS = {
    _PING_WITH_AT_CHANNEL:
        ('@channel ', 'start calling the P911 list'),
    _PING_WITH_AT_HERE:
        ('@here ', 'text and email the support DRI'),
    _SUPPRESS_PING:
        ('', 'text and email the person on-ping'),
}


# See 'Configuration' docstring for what these do.
CHANNELS = {
    '#1s-and-0s':
        Configuration(channel_type=_FIRST_PARTY,
                      high_priority_action=_PING_WITH_AT_CHANNEL,
                      medium_priority_action=_PING_WITH_AT_CHANNEL,
                      low_priority_action=_SUPPRESS_PING),
    '#content':
        Configuration(channel_type=_FIRST_PARTY,
                      high_priority_action=_SUPPRESS_PING,
                      medium_priority_action=_SUPPRESS_PING,
                      low_priority_action=_SUPPRESS_PING),
    '#user-issues':
        Configuration(channel_type=_THIRD_PARTY,
                      high_priority_action=_PING_WITH_AT_HERE,
                      medium_priority_action=_PING_WITH_AT_HERE,
                      low_priority_action=_PING_WITH_AT_HERE),
}


def format_message(incident, channel, should_ping=True):
    summary = (incident.get('trigger_summary_data', {})
               .get('subject', '<no summary available>'))

    (channel_type,
     high_priority_action,
     medium_priority_action,
     low_priority_action) = CHANNELS[channel]

    is_p911 = incident['urgency'] == 'high'
    is_weekday = _now_us_pacific().weekday() < 5

    priority = 'P911' if is_p911 else 'P0'

    action = (high_priority_action if is_p911 and should_ping else
              medium_priority_action if is_weekday and should_ping else
              low_priority_action)
    (at_mention, next_steps) = _ACTIONS[action]

    base_message = _BASE_MESSAGES[channel_type]

    return base_message.format(
        at_mention=at_mention,
        priority=priority,
        url=incident['html_url'],
        number=incident['incident_number'],
        summary=summary,
        next_steps=next_steps)


def _now_us_pacific():
    """Get the current date, in US/Pacific time."""
    # Late import so that we can avoid this in tests.
    from third_party.pytz.gae import pytz
    return datetime.datetime.now(pytz.timezone('US/Pacific'))
