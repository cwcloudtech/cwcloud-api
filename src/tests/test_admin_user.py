import os

from unittest import TestCase
from unittest.mock import Mock, patch
from fastapi.responses import JSONResponse

from entities.User  import User

test_current_user = Mock()
mock_db = Mock()
mock_bt = Mock()

class TestAdminUser(TestCase):
    def setUp(self):
        """Set up test fixtures before each test method"""
        self.test_password = os.getenv('TEST_USER_PASSWORD', 'dummy_password_for_tests')
    
    
    def __init__(self, *args, **kwargs):
        super(TestAdminUser, self).__init__(*args, **kwargs)
    
    @patch('entities.User.User.getAllUsers', side_effect = lambda x: [])
    @patch('utils.paginator.get_paginated_list', side_effect = lambda w,x,y,z: [])
    def test_admin_get_users(self, getAllUsers, get_paginated_list):    
        # Given
        from controllers.admin.admin_user import admin_get_users
        from entities.User import User
        no_per_page  = 10
        page = 1
        test_user = User(
            id=1, 
            email='Test@gmail.com', 
            password=self.test_password, 
            confirmed=True, 
            is_admin=True
        )
        get_paginated_list.return_value = [test_user]
        getAllUsers.return_value = test_user

        # When
        result = admin_get_users(test_current_user, no_per_page, page, mock_db)
        response_status_code = result.__dict__['status_code']

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), '{"result":{"page":1,"no_per_page":10,"count":0,"previous":"","next":"","data":[]}}')
    
    @patch('entities.User.User.getUserById', side_effect = lambda x,y:[]) 
    def test_admin_get_user(self, getUserById):
        # Given
        from controllers.admin.admin_user import admin_get_user
        from entities.User import User
        userId = 1
        getUserById.return_value = User(id= userId)

        # When
        result = admin_get_user(test_current_user, userId, mock_db)
        response_status_code = result.__dict__['status_code']

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(),'{"status":"ok","result":[]}')
    
    @patch('utils.common.is_numeric')
    @patch('entities.User.User.getUserById', side_effect = lambda x,y : User(id= 1 ))    
    @patch('entities.Apikeys.ApiKeys.deleteUserAllApiKeys', side_effect = lambda x,y:[])
    @patch('entities.User.User.getFirstAdminUser', side_effect = lambda x:[])
    @patch('entities.faas.Function.FunctionEntity.transferAllFunctionsOwnership', side_effect = lambda x,y,z:[])
    @patch('entities.faas.Trigger.TriggerEntity.transferAllTriggersOwnership', side_effect = lambda x,y,z:[])
    @patch('entities.faas.Invocation.InvocationEntity.transferAllInvocationsOwnership', side_effect = lambda x,y,z:[])
    @patch('entities.User.User.deleteUserById', side_effect = lambda x,y:[])
    def test_admin_remove_user(self, is_numeric, getUserById, deleteUserAllApiKeys, getFirstAdminUser, transferAllFunctionsOwnership, transferAllTriggersOwnership, transferAllInvocationsOwnership, deleteUserById):
        # Given
        from controllers.admin.admin_user import admin_remove_user
        userId = 1
        getUserById.return_value = User(id= userId)

        # When
        result = admin_remove_user(test_current_user, userId, mock_db)
        response_status_code = result.__dict__['status_code']

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200) 
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), '{"status":"ok","message":"user successfully deleted","i18n_code":"user_deleted"}')
    
    @patch('utils.common.is_numeric')
    @patch('entities.User.User.getUserById', side_effect = lambda x,y : User(id= 1 ))    
    @patch('entities.User.User.updateConfirmation', side_effect = lambda x,y,z:[])    
    def test_admin_update_user_confirmation(self, is_numeric, getUserById, updateConfirmation ):
        # Given
        from controllers.admin.admin_user import admin_update_user_confirmation
        userId = 1
        getUserById.return_value = User(id= userId)

        # When
        result = admin_update_user_confirmation(test_current_user, userId, mock_db)
        response_status_code = result.__dict__['status_code']

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), '{"status":"ok","message":"user successfully confirmed","i18n_code":"user_confirmed"}')    
    
    @patch('utils.common.is_numeric')
    @patch('entities.User.User.getUserById', side_effect = lambda x,y : User(id= 1 ))    
    @patch('entities.User.User.updateConfirmation', side_effect = lambda x,y,z:[])    
    def test_admin_update_user_role(self, is_numeric, getUserById, updateConfirmation ):
        # Given
        from controllers.admin.admin_user import admin_update_user_role
        from entities.User import User
        from schemas.User import UserAdminUpdateRoleSchema
        userId = 1
        payload = UserAdminUpdateRoleSchema(is_admin=True)
        getUserById.return_value = User(id= userId)

        # When
        result = admin_update_user_role(test_current_user, userId, payload,  mock_db)
        response_status_code = result.__dict__['status_code']

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200) 
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), '{"status":"ok","message":"user successfully updated","i18n_code":"user_updated"}')
    
    @patch('utils.common.is_numeric')
    @patch('entities.User.User.getUserById', side_effect = lambda x,y : User(id= 1 ))    
    @patch('entities.Mfa.Mfa.deleteUserMethods', side_effect = lambda x,y:[])
    def test_admin_delete_user_2fa(self, is_numeric, getUserById, deleteUserMethods ):
        # Given
        from controllers.admin.admin_user import admin_delete_user_2fa
        userId = 1
        getUserById.return_value = User(id= userId)

        # When
        result = admin_delete_user_2fa(test_current_user, userId, mock_db)
        response_status_code = result.__dict__['status_code']
        
       # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), '{"status":"ok","message":"2fa successfully deleted","i18n_code":"2fa_deleted"}')

    @patch('utils.security.is_not_email_valid')
    @patch('entities.User.User.getUserByEmail', side_effect = lambda x,y: User(id=1, email='john.doe@example.com'))
    def test_admin_update_user(self, getUserByEmail, is_not_email_valid):
        # Given
        from controllers.admin.admin_user import admin_update_user
        from entities.User import User
        from schemas.User import UserAdminUpdateSchema, EnabledFeatures
        userId = 1
        enabled_features = EnabledFeatures(
            without_vat = False,
            auto_pay = False,
            emailapi = False,
            cwaiapi = False,
            faasapi = False,
            disable_emails = False,
            k8sapi = False,
            daasapi = False,
            iotapi = False,
            ban = False
        )
        payload = UserAdminUpdateSchema(
            email='john.doe@example.com', 
            is_admin = True, 
            registration_number='1',
            address = '1',
            company_name = '1', 
            contact_info = '1', 
            confirmed = True, 
            enabled_features = enabled_features
        )  
        is_not_email_valid.return_value = False                                   
        getUserByEmail.return_value = User(email='john.doe@example.com' , id = userId)

        # When
        result = admin_update_user(test_current_user, userId, payload, mock_db)
        response_status_code = result.__dict__['status_code']

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), '{"status":"ok","message":"user successfully updated","i18n_code":"user_updated"}')
    
