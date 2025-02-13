from unittest import TestCase
from unittest.mock import Mock, patch

test_current_user = Mock()
mock_user_auth = Mock()
mock_db = Mock()
mock_bt = Mock()

class TestInvocations(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestInvocations, self).__init__(*args, **kwargs)

    @patch.dict('os.environ', {'CONSUMER_GROUP': 'test_consumer_group', 'CONSUMER_CHANNEL': 'test_consumer_channel'})
    @patch('utils.common.is_empty', side_effect=lambda x: False)
    @patch('utils.common.is_not_empty', side_effect=lambda x: True)
    @patch('utils.faas.invoker.get_invoker_id', side_effect=lambda x, y:  1)
    @patch('controllers.faas.invocations.invoke', side_effect=lambda payload, current_user, user_auth, db: {'status': 'ok', 'code': 202})
    def test_invoke(self, is_not_empty, get_invoker_id, is_empty, invoke):
        # Given
        from controllers.faas.invocations import invoke
        from schemas.faas.Invocation import Invocation
        from schemas.faas.Invocation import InvocationContent
        from schemas.faas.InvocationArg import InvocationArgument
        from schemas.UserAuthentication import UserAuthentication
        
        invocation_arg = InvocationArgument(
            key = 'key',
            value = 'value'
        )
        
        user_auth = UserAuthentication(
            is_authenticated=True,
            header_key="Authorization",
            header_value="Bearer token"
        )
        
        invocation_content = InvocationContent(
            function_id = "1",
            args = [invocation_arg],
            state = '',
            result = '',
            user_id = "1",
            user_auth = user_auth
        )
        
        invocation = Invocation(
            invoker_id = 1,
            content = invocation_content
        )        
        
        get_invoker_id.return_value = invocation
        
        # When
        result = invoke(invocation, test_current_user, mock_user_auth, mock_db)
        
        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['code'], 202)
    
    @patch.dict('os.environ', {'CONSUMER_GROUP': 'test_consumer_group', 'CONSUMER_CHANNEL': 'test_consumer_channel'})
    @patch('utils.common.is_empty', side_effect=lambda x: x)
    @patch('utils.faas.invoker.override_invoker_id', side_effect=None)
    @patch('controllers.faas.invocations.complete', side_effect=lambda x, y, z, db: {'status': 'ok', 'code': 200, 'id': x, 'updated_at': y.updated_at})
    def test_complete(self, is_empty, override_invoker_id, complete):
        # Given
        from controllers.faas.invocations import complete
        from schemas.faas.Invocation import CompletedInvocation
        from schemas.faas.Invocation import InvocationContent
        from schemas.faas.InvocationArg import InvocationArgument
        from schemas.UserAuthentication import UserAuthentication
        
        invocation_arg = InvocationArgument(
            key = 'key',
            value = 'value'
        )
        
        user_auth = UserAuthentication(
            is_authenticated=True,
            header_key="Authorization",
            header_value="Bearer token"
        )
           
        invocation_content = InvocationContent(
            function_id = "1",
            args = [invocation_arg],
            state = '',
            result = '',
            user_id = "1",
            user_auth = user_auth
        )
        
        invocation = CompletedInvocation(
            id = "1",
            invoker_username = "test_user",
            created_at = '2020-01-01 00:00:00',
            updated_at = '2020-01-01 00:00:00',
            content= invocation_content,
            invoker_id=1
        )
        
        override_invoker_id.return_value = invocation
        
        # When
        result = complete(1, invocation, test_current_user, mock_db)
        
        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['code'], 200)
        self.assertEqual(result['id'], 1)
        self.assertEqual(result['updated_at'], '2020-01-01 00:00:00')
        
    @patch.dict('os.environ', {'CONSUMER_GROUP': 'test_consumer_group', 'CONSUMER_CHANNEL': 'test_consumer_channel'})
    @patch('controllers.faas.invocations.get_invocation', side_effect=lambda x, y, z: {'status': 'ok', 'code': 200, 'id': 1, 'updated_at': '2020-01-01  00:00:00'})
    def test_get_invocation(self, get_invocation):
        # Given
        from controllers.faas.invocations import get_invocation
        
        # When
        result = get_invocation(1, test_current_user, mock_db)
        
        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['code'], 200)
        self.assertEqual(result['id'], 1)
        self.assertEqual(result['updated_at'], '2020-01-01  00:00:00')
    
    @patch.dict('os.environ', {'CONSUMER_GROUP': 'test_consumer_group', 'CONSUMER_CHANNEL': 'test_consumer_channel'})
    @patch('controllers.faas.invocations.delete_invocation', side_effect=lambda x, y, z: {'status': 'ok', 'code': 200})    
    def test_delete_invocation(self, delete_invocation):
        # Given
        from controllers.faas.invocations import delete_invocation
        
        # When
        result = delete_invocation(1, test_current_user, mock_db)
        
        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['code'], 200)
    
    @patch.dict('os.environ', {'CONSUMER_GROUP': 'test_consumer_group', 'CONSUMER_CHANNEL': 'test_consumer_channel'})
    @patch('controllers.faas.invocations.clear_my_invocations', side_effect=lambda x, y: {'status': 'ok', 'code': 200})
    def test_clear_my_invocations(self, clear_my_invocations):
        # Given
        from controllers.faas.invocations import clear_my_invocations
        
        # When
        result = clear_my_invocations(test_current_user, mock_db)
        
        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['code'], 200)
    
    @patch.dict('os.environ', {'CONSUMER_GROUP': 'test_consumer_group', 'CONSUMER_CHANNEL': 'test_consumer_channel'})
    @patch('controllers.faas.invocations.get_my_invocations', side_effect=lambda x, y: {'status': 'ok', 'code': 200, 'start_index': 'start_index', 'max_results': 'max_results', 'results': 'results'})    
    def test_get_my_invocations(self, get_my_invocations):
        # Given
        from controllers.faas.invocations import get_my_invocations
        
        # When
        result = get_my_invocations(test_current_user, mock_db)
        
        # Then
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['code'], 200)
        self.assertEqual(result['start_index'], 'start_index')
        self.assertEqual(result['max_results'], 'max_results')
    
    @patch.dict('os.environ', {'CONSUMER_GROUP': 'test_consumer_group', 'CONSUMER_CHANNEL': 'test_consumer_channel'})
    @patch('controllers.faas.invocations.get_all_invocations', side_effect=lambda db, current_user, start_index, max_results: {'status': 'ok', 'code': 200, 'start_index': start_index,
    'max_results': max_results, 'results': [{"id": 1, "content": {}, "created_at": '2020-01-01', "updated_at": '2020-01-01', "invoker": {"id": 1, "username": "test_user"}}]})    
    def test_get_all_invocations(self, get_all_invocations):
        # Given
        from controllers.faas.invocations import get_all_invocations
        
        # When
        result = get_all_invocations(mock_db, test_current_user, start_index= 'start_index', max_results= 'max_results')
        
        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['code'], 200)
        self.assertEqual(result['start_index'], 'start_index')
        self.assertEqual(result['max_results'], 'max_results')
        self.assertEqual(result['results'], [
            {
                "id": 1,
                "content": {},
                "created_at": '2020-01-01',
                "updated_at": '2020-01-01',
                "invoker": {
                    "id": 1,
                    "username": "test_user"
                }
            }
        ])
