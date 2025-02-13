from unittest import TestCase
from unittest.mock import Mock, patch

test_current_user = Mock()
mock_db = Mock()
mock_bt = Mock()

class TestFunction(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestFunction, self).__init__(*args, **kwargs)
    
    @patch('controllers.faas.functions.get_owner_id', side_effect=lambda x,y: 1) 
    @patch('controllers.faas.functions.add_function', side_effect=lambda x,y,z: {'code': 201, 'id':  1, 'created_at': '2020-01-01', 'updated_at': '2020-01-01'})
    def test_add_function(self, add_function, get_owner_id):
        # Given
        from controllers.faas.functions import add_function
        from schemas.faas.Function import BaseFunction
        from schemas.faas.FunctionContent import FunctionContent
        
        function_content = FunctionContent(
            code = 'function foo(arg): {return "bar " + arg;}',
            language = 'javascript',
            name = 'foo',
            args = ['arg'],
            blockly = None,
            callbacks = None,
            regexp = None,
            env = None
        )
        
        function = BaseFunction(
            is_public = True,
            owner_id = 1,
            content = function_content
        )
        
        get_owner_id.return_value = function
        
        # When        
        result = add_function(function, test_current_user, mock_db)
        
        # Then
        self.assertEqual(result['code'], 201)
        self.assertIsNotNone(result['id'])
        self.assertIsNotNone(result['created_at'])
        self.assertIsNotNone(result['updated_at'])
     
    @patch('utils.faas.owner.override_owner_id', side_effect=lambda x, y, z: x)
    @patch('utils.faas.security.has_not_write_right', side_effect=lambda x, y: x)
    @patch('utils.faas.functions.is_not_supported_language', side_effect=lambda x: x)
    @patch('controllers.faas.functions.override_function', side_effect=lambda id, function, current_user, db: {'status': 'ok', 'code': 200, 'updated_at': '2020-01-01'})
    def test_override_function(self, override_owner_id, has_no_right, is_not_supported_language, override_function):
        # Given
        from controllers.faas.functions import override_function
        from schemas.faas.Function import Function
        from schemas.faas.FunctionContent import FunctionContent
        
        function_content = FunctionContent(
            code = 'function foo(arg): {return "bar " + arg;}',
            language = 'javascript',
            name = 'foo',
            args = ['arg'],
            blockly = None,
            callbacks = None,
            regexp = None,
            env = None
        )
        
        function = Function(
            id = '1',
            owner_username = '1',
            created_at = '2020-01-01',
            updated_at = '2020-01-01',
            is_public = True,
            owner_id = 1,
            content = function_content
        )
        
        override_owner_id.return_value = function
        
        # When
        result = override_function(1, function, test_current_user, mock_db)

        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['code'], 200)
        self.assertIsNotNone(result['updated_at'])
            
    @patch('controllers.faas.functions.delete_function', side_effect=lambda x, y, z: {'status': 'ok', 'code': 200})
    def test_delete_function(self, delete_function):
        # Given
        from controllers.faas.functions import delete_function
        
        # When
        result = delete_function(1, test_current_user, mock_db)
        
        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['code'], 200)
    
    @patch('controllers.faas.functions.get_function', side_effect=lambda x, y, z: {'status': 'ok', 'code': 200, 'entity': 'db_function'})
    @patch('utils.faas.security.has_not_write_right', side_effect=lambda x, y: x)
    def test_get_function(self, get_function, has_not_write_right):
        # Given
        from controllers.faas.functions import get_function
        
        # When
        result = get_function(1, test_current_user, mock_db)
        
        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['code'], 200)
        self.assertEqual(result['entity'], 'db_function')
            
    @patch('controllers.faas.functions.get_my_functions', side_effect=lambda db, current_user, start_index, max_results: {'status': 'ok', 'code': 200, 'start_index': start_index, 'max_results': max_results, 'results': []})
    @patch('utils.common.is_not_numeric', return_value=False)
    def test_get_my_functions(self, get_my_functions, is_not_numeric):
        # Given
        from controllers.faas.functions import get_my_functions
        
        # When
        result = get_my_functions(mock_db, test_current_user, start_index='start_index', max_results='max_results')
        
        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['code'], 200)
        self.assertEqual(result['start_index'], 'start_index')
        self.assertEqual(result['max_results'], 'max_results')
        self.assertEqual(result['results'], [])

    @patch('controllers.faas.functions.get_all_functions', side_effect=lambda db, current_user, start_index, max_results: {'status': 'ok', 'code': 200, 'start_index': start_index,
    'max_results': max_results, 'results': [{"id": 1, "is_public": True, "content": {}, "created_at": '2020-01-01', "updated_at": '2020-01-01', "owner": {"id": 1, "username": "test_user"}}]})
    @patch('utils.common.is_false', return_value=False)
    @patch('utils.common.is_not_numeric', return_value=False)
    def test_get_all_functions(self, get_all_functions, is_false, is_not_numeric):
        # Given
        from controllers.faas.functions import get_all_functions
      
        # When
        result = get_all_functions(mock_db, test_current_user, start_index='start_index', max_results='max_results')
        
        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['code'], 200)
        self.assertEqual(result['start_index'], 'start_index')
        self.assertEqual(result['max_results'], 'max_results')
        self.assertEqual(result['results'], [
            {
                "id": 1,
                "is_public": True,
                "content": {},
                "created_at": '2020-01-01',
                "updated_at": '2020-01-01',
                "owner": {
                    "id": 1,
                    "username": "test_user"
                }
            }
        ])
