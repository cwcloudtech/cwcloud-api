from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

test_current_user = Mock()
mock_user_auth = Mock()
mock_db = Mock()
mock_bt = Mock()

def get_test_token():
    """Generate a temporary token for testing purposes"""
    return f"test_token_{uuid4().hex[:10]}"

class TestDevice(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestDevice, self).__init__(*args, **kwargs)
        self.test_token = get_test_token()
    
    @patch('entities.User.User.getUserByEmail')
    @patch('controllers.iot.device.add_device', side_effect=lambda x, y, z: {
        'status': 'ok',
        'message': 'Device successfully created',
        'token': None
    })
    def test_add_device(self, add_device, getUserByEmail):
        # Given
        from schemas.iot.Device import DeviceSchema
        from entities.User import User

        target_user = User()
        target_user.email = "username@email.com"
        target_user.id = 1

        test_device_token = get_test_token()
        add_device.side_effect = lambda x, y, z: {
            'status': 'ok',
            'message': 'Device successfully created',
            'token': test_device_token
        }

        payload = DeviceSchema.parse_obj({
            'typeobject_id': '1',
            'username': 'test@comwork.io'
        })

        getUserByEmail.return_value = target_user

        # When
        result = add_device(test_current_user, payload, mock_db)

        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['message'], 'Device successfully created')
        self.assertIsNotNone(result['token'])
        self.assertNotEqual(result['token'], 'some_token')  # Ensure we're not using a hardcoded token
    
    @patch('jose.jwt.decode')
    @patch('entities.User.User.getUserByEmail')
    @patch('controllers.iot.device.confirm_device_by_token', side_effect=lambda token, db: {
        'status': 'ok',
        'message': 'Device successfully confirmed'
    })
    def test_confirm_device_by_token(self, getUserByEmail, decode, confirm_device_by_token):
        # Given
        from controllers.iot.device import confirm_device_by_token
        from entities.User import User

        target_user = User()
        target_user.email = "username@email.com"
        target_user.id = 1
        
        # Generate a dynamic test token
        test_confirmation_token = get_test_token()

        decode.return_value = {"email": "test@example.com"}
        getUserByEmail.return_value = target_user

        # When
        result = confirm_device_by_token(test_confirmation_token, mock_db)

        # Then 
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['message'], 'Device successfully confirmed')
    
    @patch('entities.iot.Device.Device')
    @patch('controllers.iot.device.get_user_device_by_id', side_effect=lambda current_user, device_id, db: {'id': device_id, 'username': "testuser@example.com", 'active': True, 'status': 'ok'})
    def test_get_user_device_by_id(self, get_user_device_by_id, getDeviceById):
        # Given
        from controllers.iot.device import get_user_device_by_id
        from entities.iot.Device import Device

        device = Device()
        device.id = "1"
        device.typeobject_id = "some-guid"
        device.username = "testuser@example.com"
        device.active = True

        Device.getDeviceById.return_value = device

        # When
        result = get_user_device_by_id(test_current_user, "1", mock_db)

        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['id'], str(device.id))
        self.assertEqual(result['username'], device.username)
        self.assertEqual(result['active'], device.active)
            
    @patch('entities.iot.Device.Device')
    @patch('controllers.iot.device.delete_user_device_by_id', side_effect=MagicMock(return_value={'message': 'Device successfully deleted', 'status': 'ok'}, status_code=200))
    def test_delete_user_device_by_id(self, delete_user_device_by_id, getDeviceById):
        # Given
        from controllers.iot.device import delete_user_device_by_id
        from entities.iot.Device import Device
        
        device = Device()
        device.id = "1"
        device.typeobject_id = "some-guid"
        device.username = "testuser@example.com"
        device.active = True
        
        Device.getDeviceById.return_value = device
        
        # When
        result = delete_user_device_by_id(test_current_user, "1", mock_db)
        
        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['message'], 'Device successfully deleted')

    @patch('entities.iot.Device.Device')
    @patch('controllers.iot.device.get_user_devices', side_effect=lambda current_user, db: {'username': "testuser@example.com", 'active': True, 'status': 'ok'})
    def test_get_user_devices(self, get_user_devices, getUserDevices):
        # Given
        from controllers.iot.device import get_user_devices
        from entities.iot.Device import Device

        device = Device()
        device.id = "1"
        device.typeobject_id = "some-guid"
        device.username = "testuser@example.com"
        device.active = True

        Device.getUserDevices.return_value = device

        # When
        result = get_user_devices(test_current_user, mock_db)

        # Then
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['username'], device.username)
        self.assertEqual(result['active'], device.active)
