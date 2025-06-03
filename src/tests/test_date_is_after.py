import time

from unittest import TestCase

from utils.date import _date_hour_format_iso, is_after_current_time

class TestDateIsAfter(TestCase):
    def test_is_after_current_time_nominal(self):
        # Given
        current_date_str = time.strftime(_date_hour_format_iso, time.gmtime())

        # When
        result = is_after_current_time(current_date_str)

        # Then
        self.assertTrue(result)

    def test_is_after_current_time_timezone(self):
        # Given
        current_date_str = "{}.000Z".format(time.strftime(_date_hour_format_iso, time.gmtime()))

        # When
        result = is_after_current_time(current_date_str)

        # Then
        self.assertTrue(result)

    def test_is_after_current_time_ko(self):
        # Given
        current_date_str = "2022-03-08T12:00:00"

        # When
        result = is_after_current_time(current_date_str)

        # Then
        self.assertFalse(result)
