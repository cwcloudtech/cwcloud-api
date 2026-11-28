"""Admin API keys: create a key for another user, list them with the owner's email."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from controllers import api_keys as controller
from schemas.API_keys import ApiKeysAdminSchema

ADMIN = SimpleNamespace(id = 1, email = 'admin@example.com')


class TestAdminApiKeys(unittest.TestCase):
    @patch('controllers.api_keys.ApiKeys')
    @patch('controllers.api_keys.User')
    def test_key_is_created_for_the_target_user(self, user, api_keys):
        user.getUserByEmail.return_value = SimpleNamespace(id = 42, email = 'bob@example.com')
        api_keys.getApiKeysByAccessKey.return_value = []
        api_keys.getApiKeysBySecretKey.return_value = []
        created = MagicMock()
        api_keys.return_value = created
        with patch('controllers.api_keys.json.dumps', return_value = '{"name": "ci"}'):
            response = controller.admin_create_api_key(ADMIN, ApiKeysAdminSchema(email = 'bob@example.com', name = 'ci'), MagicMock())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(created.user_id, 42)
        created.save.assert_called_once()

    @patch('controllers.api_keys.User')
    def test_unknown_user_is_a_404(self, user):
        user.getUserByEmail.return_value = None
        response = controller.admin_create_api_key(ADMIN, ApiKeysAdminSchema(email = 'nobody@example.com', name = 'ci'), MagicMock())
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'user_not_found', response.body)

    @patch('controllers.api_keys.ApiKeys')
    @patch('controllers.api_keys.User')
    def test_list_carries_the_owner_email_and_never_the_secret(self, user, api_keys):
        api_keys.getAllApiKeys.return_value = [SimpleNamespace(id = 3, name = 'ci', user_id = 42, created_at = 'x', secret_key = 'SECRET')]
        user.getUserById.return_value = SimpleNamespace(email = 'bob@example.com')
        response = controller.admin_get_api_keys(MagicMock())
        self.assertIn(b'bob@example.com', response.body)
        self.assertNotIn(b'SECRET', response.body)


if __name__ == '__main__':
    unittest.main()
