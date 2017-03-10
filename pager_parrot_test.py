import datetime
import mock
import unittest

import pager_parrot


# Some first- and third-party channel names.
_CHANNEL_1P = "#nonexistent-test-channel-do-not-create"
_CHANNEL_3P = "#nonexistent-test-channel-do-not-create-third-party"


class PagerParrotLogicTest(unittest.TestCase):
    """Test all configurations of the pager parrot behavior."""

    def setUp(self):
        super(PagerParrotLogicTest, self).setUp()

        # Mock out the pager parrot's CHANNELS set for testing.
        # Fortunately, we have as many actions as we have priority categories,
        # so we can test them all by creating a widespread configuration.
        config_1p = pager_parrot.Configuration(
            channel_type=pager_parrot._FIRST_PARTY,
            high_priority_action=pager_parrot._PING_WITH_AT_CHANNEL,
            medium_priority_action=pager_parrot._PING_WITH_AT_HERE,
            low_priority_action=pager_parrot._SUPPRESS_PING)
        config_3p = pager_parrot.Configuration(
            channel_type=pager_parrot._THIRD_PARTY,
            high_priority_action=pager_parrot._PING_WITH_AT_CHANNEL,
            medium_priority_action=pager_parrot._PING_WITH_AT_HERE,
            low_priority_action=pager_parrot._SUPPRESS_PING)
        patcher = mock.patch.dict(
            pager_parrot.CHANNELS,
            clear=True,
            values={
                _CHANNEL_1P: config_1p,
                _CHANNEL_3P: config_3p,
            }
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_high_priority_1p_weekday(self):
        incident = self._urgent_incident()
        with _mocking_weekday():
            result = pager_parrot.format_message(incident, _CHANNEL_1P)
            self.assertIn('@channel', result)
            self.assertIn('start calling the P911 list', result)

    def test_high_priority_1p_weekend(self):
        incident = self._urgent_incident()
        with _mocking_weekend():
            result = pager_parrot.format_message(incident, _CHANNEL_1P)
            self.assertIn('@channel', result)
            self.assertIn('start calling the P911 list', result)

    def test_high_priority_3p_weekday(self):
        incident = self._urgent_incident()
        with _mocking_weekday():
            result = pager_parrot.format_message(incident, _CHANNEL_3P)
            self.assertIn('@channel', result)
            self.assertIn('dev team has been alerted', result)

    def test_high_priority_3p_weekend(self):
        incident = self._urgent_incident()
        with _mocking_weekend():
            result = pager_parrot.format_message(incident, _CHANNEL_3P)
            self.assertIn('@channel', result)
            self.assertIn('dev team has been alerted', result)

    def test_medium_priority_1p(self):
        incident = self._non_urgent_incident()
        with _mocking_weekday():
            result = pager_parrot.format_message(incident, _CHANNEL_1P)
            self.assertIn('@here', result)
            self.assertIn('text and email the support DRI', result)

    def test_medium_priority_3p(self):
        incident = self._non_urgent_incident()
        with _mocking_weekday():
            result = pager_parrot.format_message(incident, _CHANNEL_3P)
            self.assertIn('@here', result)
            self.assertIn('dev team has been alerted', result)

    def test_low_priority_1p(self):
        incident = self._non_urgent_incident()
        with _mocking_weekend():
            result = pager_parrot.format_message(incident, _CHANNEL_1P)
            self.assertNotIn('@channel', result)
            self.assertNotIn('@here', result)
            self.assertIn('text and email the person on-ping', result)

    def test_low_priority_3p(self):
        incident = self._non_urgent_incident()
        with _mocking_weekend():
            result = pager_parrot.format_message(incident, _CHANNEL_3P)
            self.assertNotIn('@channel', result)
            self.assertNotIn('@here', result)
            self.assertIn('dev team has been alerted', result)

    def _non_urgent_incident(self):
        return {
            'urgency': 'low',
            'html_url': 'https://zombo.com/',
            'incident_number': 77,
        }

    def _urgent_incident(self):
        return {
            'urgency': 'high',
            'html_url': 'https://zombo.com/onfire',
            'incident_number': 78,
        }


class PagerParrotConfigurationTest(unittest.TestCase):
    """Test that the configuration is reasonable. These are not comprehensive.

    These may fail if you update the configuration; just update them, too.
    """

    def test_proper_whitespace_in_base_messages(self):
        # These are just a bit annoying in Slack.
        for base_message in pager_parrot._BASE_MESSAGES.viewvalues():
            self.assertNotIn('\n', base_message)
            self.assertEquals(len(base_message.split('  ')), 1, base_message)

    def test_1s0s_configured(self):
        self.assertIn('#1s-and-0s', pager_parrot.CHANNELS)

    def test_p911_pings_channel_in_1s0s_on_weekday(self):
        incident = self._urgent_incident()
        with _mocking_weekday():
            result = pager_parrot.format_message(incident, '#1s-and-0s')
            self.assertIn('@channel', result)

    def test_p911_pings_channel_in_1s0s_on_weekend(self):
        incident = self._urgent_incident()
        with _mocking_weekend():
            result = pager_parrot.format_message(incident, '#1s-and-0s')
            self.assertIn('@channel', result)

    def test_p0_pings_channel_in_1s0s_on_weekday(self):
        incident = self._non_urgent_incident()
        with _mocking_weekday():
            result = pager_parrot.format_message(incident, '#1s-and-0s')
            self.assertIn('@channel', result)

    def _non_urgent_incident(self):
        return {
            'urgency': 'low',
            'html_url': 'https://www.khanacademy.org/coach-reports',
            'incident_number': 498,
        }

    def _urgent_incident(self):
        return {
            'urgency': 'high',
            'html_url': 'https://www.khanacademy.org/v/the-beauty-of-algebra',
            'incident_number': 499,
        }


def _mocking_day_of_week(weekday):
    """Set the current time to the given day of the week; 0 = Monday."""
    base_monday = datetime.datetime(2016, 7, 4, 12, 22, 0)
    target_day = base_monday + datetime.timedelta(days=weekday)
    assert target_day.weekday() == weekday, (target_day.weekday(), weekday)
    return mock.patch('pager_parrot._now_us_pacific', lambda: target_day)


def _mocking_weekday():
    return _mocking_day_of_week(2)


def _mocking_weekend():
    return _mocking_day_of_week(6)


if __name__ == '__main__':
    unittest.main()
