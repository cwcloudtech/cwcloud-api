from unittest import TestCase
from unittest.mock import Mock, patch

test_current_user = Mock()
mock_user_auth = Mock()
mock_db = Mock()
mock_bt = Mock()

class TestData(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestData, self).__init__(*args, **kwargs)
    
    @patch.dict('os.environ', {'FAAS_API_URL': 'http://localhost:5000', 'API_MAX_RESULTS': '100', 'CONSUMER_GROUP': 'test_consumer_group', 'CONSUMER_CHANNEL': 'test_consumer_channel'})
    @patch('controllers.iot.data.add_data', side_effect=lambda x, y, z, w: {'status': 'ok', 'message': 'Data added successfully'})
    @patch('controllers.faas.invocations.invoke_sync', side_effect=None)
    @patch('schedule.crontabs.handle_trigger')
    def test_add_data(self, invoke_sync, findById_function, findById_object_type):
        # Given
        from controllers.iot.data import add_data
        from schemas.iot.Data import DataSchema
        from entities.iot.Device import Device

        device = Device()
        device.id = "qsd6f5qsdf656d4q4242455"
        device.typeobject_id = "qd6dq5sf6qsd5f68dqs5"
        device.username = 'admin'
        device.active = True

        object_type = Mock()
        object_type.content = {'decoding_function': 'function_id'}
        findById_object_type.return_value = object_type
        
        function = Mock()
        function.content = {'args': ['data']}
        findById_function.return_value = function
        
        invoke_sync.return_value = {'status': 'ok', 'message': 'Success', 'entity': {'content': {'result': '123'}}}

        payload = DataSchema(device_id=device.id, content="content")

        mock_user_auth = Mock()
        mock_user_auth.is_admin = True

        # When
        result = add_data(test_current_user, mock_user_auth, payload, mock_db)

        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['message'], 'Data added successfully')
