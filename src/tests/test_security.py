from typing import ClassVar
from unittest import TestCase
from utils.security import check_password, is_not_email_valid, random_password

class TestSecurity(TestCase):
    TEST_PASSWORDS: ClassVar[dict] = {
        'valid': {
            'value': 'ValidPass123$',
            'expected_status': True,
            'expected_code': None
        },
        'no_capital': {
            'value': 'lowercase123$',
            'expected_status': False,
            'expected_code': 'password_no_upper'
        },
        'no_lower': {
            'value': 'UPPERCASE123$',
            'expected_status': False,
            'expected_code': 'password_no_lower'
        },
        'no_special': {
            'value': 'NoSpecial123',
            'expected_status': False,
            'expected_code': 'password_no_symbol'
        },
        'too_short': {
            'value': 'Short1$',
            'expected_status': False,
            'expected_code': 'password_too_short'
        }
    }

    def test_check_password_nominal(self):
        # When
        check = check_password(self.TEST_PASSWORDS['valid']['value'])

        # Then
        self.assertEqual(check['status'], self.TEST_PASSWORDS['valid']['expected_status'])

    def test_check_password_missing_capital(self):
        # When
        test_case = self.TEST_PASSWORDS['no_capital']
        check = check_password(test_case['value'])

        # Then
        self.assertEqual(check['status'], test_case['expected_status'])
        self.assertEqual(check['i18n_code'], test_case['expected_code'])

    def test_check_password_missing_lower(self):
        # When
        test_case = self.TEST_PASSWORDS['no_lower']
        check = check_password(test_case['value'])

        # Then
        self.assertEqual(check['status'], test_case['expected_status'])
        self.assertEqual(check['i18n_code'], test_case['expected_code'])

    def test_check_password_no_special_char(self):
        # When
        test_case = self.TEST_PASSWORDS['no_special']
        check = check_password(test_case['value'])

        # Then
        self.assertEqual(check['status'], test_case['expected_status'])
        self.assertEqual(check['i18n_code'], test_case['expected_code'])

    def test_check_password_too_short(self):
        # When
        test_case = self.TEST_PASSWORDS['too_short']
        check = check_password(test_case['value'])

        # Then
        self.assertEqual(check['status'], test_case['expected_status'])
        self.assertEqual(check['i18n_code'], test_case['expected_code'])

    def test_is_not_email_valid(self):
        # Given
        email = "toto.titi@gmail.com"

        # When
        check = is_not_email_valid(email)

        # Then
        self.assertEqual(check, False)

    def test_is_not_email_valid_invalid(self):
        # Given
        email = "toto.titi@"

        # When
        check = is_not_email_valid(email)

        # Then
        self.assertEqual(check, True)

    def test_random_password(self):
        # When
        check = check_password(random_password(10))

        # Then
        self.assertEqual(check['status'], True)
