from datetime import datetime

from unittest import TestCase

from utils.date import parse_date

class TestParseDate(TestCase):
    def test_date_nominal(self):
        # Given
        vdate = "2019-10-11"

        # When
        fdate = parse_date(vdate)

        # Then
        self.assertEqual(fdate['status'], True)
        self.assertEqual(fdate['value'], datetime.strptime(vdate, "%Y-%m-%d"))

    def test_date_with_slashes(self):
        # Given
        vdate = "2019/10/11"

        # When
        fdate = parse_date(vdate)

        # Then
        self.assertEqual(fdate['status'], True)
        self.assertEqual(fdate['value'], datetime.strptime(vdate, "%Y/%m/%d"))

    def test_date_invalid(self):
        # Given
        vdate = "2019_10_11"

        # When
        fdate = parse_date(vdate)

        # Then
        self.assertEqual(fdate['status'], False)
        self.assertEqual(fdate['value'], vdate)

    def test_date_empty(self):
        # Given
        vdate = None

        # When
        fdate = parse_date(vdate)

        # Then
        self.assertEqual(fdate['status'], False)
        self.assertEqual(fdate['value'], None)

    def test_date_already_datetime(self):
        # Given
        vdate = datetime.strptime("1990/10/11", "%Y/%m/%d")

        # When
        fdate = parse_date(vdate)

        # Then
        self.assertEqual(fdate['status'], True)
        self.assertEqual(fdate['value'], datetime.strptime("1990/10/11", "%Y/%m/%d")  )

    def test_date_already_parsed(self):
        # Given
        vdate = "2019-10-11"

        # When
        fdate = parse_date(parse_date(vdate))

        # Then
        self.assertEqual(fdate['status'], True)
        self.assertEqual(fdate['value'], datetime.strptime(vdate, "%Y-%m-%d"))
