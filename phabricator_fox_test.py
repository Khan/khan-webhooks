# TODO(colin): fix these lint errors (http://pep8.readthedocs.io/en/release-1.7.x/intro.html#error-codes)
# pep8-disable:E128
import unittest
import re
import main
import mock
import webapp2
import json

import phabricator_fox


# These example strings were taken from the logs of
# https://console.cloud.google.com/logs/viewer?project=khan-webhooks
ADDED_REVIEWER = ("amy added a reviewer for D33318: "
            "Update hover interaction to match the spec: kimerie.")
REQUESTED_REVIEW = ("dhruv requested review of D41797: Increase "
                    "email spam time limit for devserver.")


class PhabFoxLogicTest(unittest.TestCase):
    def test_added_reviewer(self):
        match = re.match(phabricator_fox.MESSAGE_RX, ADDED_REVIEWER)
        self.assertIsNone(match)

    def test_requested_review(self):
        match = re.match(phabricator_fox.MESSAGE_RX, REQUESTED_REVIEW)
        self.assertIsNotNone(match)


class TestPhabricatorFoxHandlers(unittest.TestCase):
    def setUp(self):
        self.mock_send_to_slack = self.mock_function(
            'main._build_slack_message', return_value="test message")
        self.args = json.dumps({
            'object': {
                'phid': 'PHID-object'
            },
            'transactions': [
                {
                    'phid': 'PHID-transaction'
                }
            ]
        })

    def _activate_patcher(self, patcher):
        """Activate a patcher (returned by mock.patch()) for this test.

        Returns the patched thing.
        """
        self.addCleanup(patcher.stop)
        return patcher.start()

    def mock_function(self, function_spec, **kwargs):
        """Mock the given function for the duration of this test.

        kwargs are passed to mock.patch.  By default, we use autospec=True,
        which patches it to a mock with the same methods/signature as the one
        being replaced.

        Returns the mock.
        """
        # If you set spec or autospec, we assume you mean to override us.
        if 'spec' not in kwargs and 'autospec' not in kwargs:
            kwargs['autospec'] = True
        m = self._activate_patcher(mock.patch(function_spec, **kwargs))
        return m

    def _get_response(self, args):
        request = webapp2.Request.blank('/new-phabricator-feed')
        request.method = 'POST'
        request.body = args
        response = request.get_response(main.app)
        return response

    def test_empty_transactions(self):
        self.args = json.dumps({
            'object': {
                'phid': 'PHID-test'
            },
            'transactions': []
        })
        response = self._get_response(self.args)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(self.mock_send_to_slack.call_count, 0)

    def test_no_response(self):
        self.mock_function(
            'main._transaction_search_from_phids', return_value=None)
        response = self._get_response(self.args)
        self.assertEqual(response.status_int, 404)
        self.assertEqual(self.mock_send_to_slack.call_count, 0)

    def test_transaction_create(self):
        self.mock_function(
            'main._transaction_search_from_phids', return_value={
                'data': [{'type': 'create', 'authorPHID': "PHID-user"}]})
        self.mock_function('main._phid_query_from_phid', return_value={
            "PHID-test": {
                "phid": "PHID-test",
                "uri": "https://test",
                "name": "D123",
                "fullName": "D123: test",
                "status": "open"}})
        self.mock_function(
            'main._get_author_username', return_value="test user")
        response = self._get_response(self.args)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(self.mock_send_to_slack.call_count, 1)
        self.assertEqual(
            self.mock_send_to_slack.call_args_list[0][0][1], 'create')

    def test_transaction_abandon(self):
        self.mock_function(
            'main._transaction_search_from_phids', return_value={
                'data': [{'type': 'abandon', 'authorPHID': "PHID-user"}]})
        self.mock_function('main._phid_query_from_phid', return_value={
            "PHID-test": {
                "phid": "PHID-test",
                "uri": "https://test",
                "name": "D123",
                "fullName": "D123: test",
                "status": "open"}})
        self.mock_function(
            'main._get_author_username', return_value="test user")
        response = self._get_response(self.args)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(self.mock_send_to_slack.call_count, 1)
        self.assertEqual(
            self.mock_send_to_slack.call_args_list[0][0][1], 'abandon')


if __name__ == '__main__':
    unittest.main()
