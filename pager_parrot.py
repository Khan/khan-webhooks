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


def _preprocess_base_message(msg):
    """Dedent and collapse newlines."""
    return ' '.join(textwrap.dedent(msg.strip()).split('\n'))


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
                      medium_priority_action=_SUPPRESS_PING,
                      low_priority_action=_SUPPRESS_PING),
    '#support':
        Configuration(channel_type=_FIRST_PARTY,
                      high_priority_action=_PING_WITH_AT_CHANNEL,
                      medium_priority_action=_PING_WITH_AT_CHANNEL,
                      low_priority_action=_SUPPRESS_PING),
    '#content':
        Configuration(channel_type=_FIRST_PARTY,
                      high_priority_action=_SUPPRESS_PING,
                      medium_priority_action=_SUPPRESS_PING,
                      low_priority_action=_SUPPRESS_PING),
    '#volunteer-guides':
        Configuration(channel_type=_THIRD_PARTY,
                      high_priority_action=_PING_WITH_AT_HERE,
                      medium_priority_action=_PING_WITH_AT_HERE,
                      low_priority_action=_PING_WITH_AT_HERE),
}


def format_message(incident, channel):
    summary = (incident.get('trigger_summary_data', {})
               .get('subject', '<no summary available>'))

    (channel_type,
     high_priority_action,
     medium_priority_action,
     low_priority_action) = CHANNELS[channel]

    is_p911 = incident['urgency'] == 'high'
    is_weekday = _now_us_pacific().weekday() < 5

    priority = 'P911' if is_p911 else 'P0'

    action = (high_priority_action if is_p911 else
              medium_priority_action if is_weekday else
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
