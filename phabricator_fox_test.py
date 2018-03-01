# TODO(colin): fix these lint errors (http://pep8.readthedocs.io/en/release-1.7.x/intro.html#error-codes)
# pep8-disable:E128
import unittest
import re

import phabricator_fox


# These example strings were taken from the logs of
# https://console.cloud.google.com/logs/viewer?project=khan-webhooks
ABANDONED_TEXT = ("kevinb abandoned D33306: "
                  "Remove most the lint in CircularProgressIcon.")
CREATED_TEXT = ("amy created D33337: "
                "Separate out item attempts from task completion.")
ADDED_REVIEWER = ("amy added a reviewer for D33318: "
            "Update hover interaction to match the spec: kimerie.")
REQUESTED_REVIEW = ("dhruv requested review of D41797: Increase "
                    "email spam time limit for devserver.")


class PagerParrotLogicTest(unittest.TestCase):
    def test_created_message(self):
        match = re.match(phabricator_fox.MESSAGE_RX, CREATED_TEXT)
        self.assertIsNotNone(match)

    def test_abandoned_message(self):
        match = re.match(phabricator_fox.MESSAGE_RX, ABANDONED_TEXT)
        self.assertIsNotNone(match)

    def test_added_reviewer(self):
        match = re.match(phabricator_fox.MESSAGE_RX, ADDED_REVIEWER)
        self.assertIsNone(match)

    def test_requested_review(self):
        match = re.match(phabricator_fox.MESSAGE_RX, REQUESTED_REVIEW)
        self.assertIsNotNone(match)


if __name__ == '__main__':
    unittest.main()
