from unittest import TestCase
from unittest.mock import Mock, patch
from uuid import uuid4
from fastapi.responses import JSONResponse

test_current_user = Mock()
mock_db = Mock()
mock_bt = Mock()

def get_test_token():
    """Generate a temporary token for testing purposes"""
    return f"test_{uuid4().hex[:10]}"

class TestAdminInstance(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestAdminInstance, self).__init__(*args, **kwargs)
        self.test_token = get_test_token()
        self.test_access_token = get_test_token()

    @patch('entities.Instance.Instance.getAllInstancesByRegion', side_effect = lambda x, y, z: [])
    def test_admin_get_instances(self, getAllInstancesByRegion):
        # Given
        from controllers.admin.admin_instance import admin_get_instances

        # When
        result = admin_get_instances(test_current_user, "scaleway", "fr-par", mock_db)
        response_status_code = result.__dict__['status_code']
       
        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), "[]")

    @patch('entities.Instance.Instance.findInstanceById')
    def test_admin_get_instance(self, findInstanceById):
        # Given
        from controllers.admin.admin_instance import admin_get_instance
        from entities.Instance import Instance
        from entities.Environment import Environment
        from entities.Project import Project
        instance_id = 1
        instance = Instance()
        instance.hash = "aabbcc"
        instance.name = "test-instance"
        instance.type = "DEV1-S"
        instance.provider = "scaleway"
        instance.region = "fr-par"
        instance.zone = "1"
        instance.status = "deleted"
        instance.root_dns_zone = "comwork.cloud"
        instance.user_id = 1
        instance.id = instance_id
        instance.is_protected = False

        environment = Environment()
        environment.name = "code"
        environment.path = "code"
        environment.description = "code environment"
        environment.is_private = False
        environment.logo_url = "https://whatever.com/logo.png"
        environment.environment_template = ""
        environment.doc_template = ""
        environment.roles = "code"
        environment.subdomains = "comwork.cloud"
        environment.id = 1

        project = Project()
        project.name = "test_project"
        project.url = "https://gitlab.comwork.io/dynamic/test_project"
        project.user_id = 1
        project.gitlab_url = "https://gitlab.comwork.io"
        project.gitlab_username = "amirghedira"
        project.gitlab_token = self.test_token
        project.gitlab_project_id = "1"
        project.type = "vm"
        project.id = 1

        instance.environment = environment
        instance.project = project
        findInstanceById.return_value = instance

        # When
        result = admin_get_instance(test_current_user, instance_id, mock_db)
        response_status_code = result.__dict__['status_code']
       
        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), f'{{"created_at":null,"environment_id":null,"hash":"aabbcc","id":1,"ip_address":null,"is_protected":false,"modification_date":null,"name":"test-instance","project_id":null,"provider":"scaleway","region":"fr-par","root_dns_zone":"comwork.cloud","status":"deleted","type":"DEV1-S","user":null,"user_id":1,"zone":"1","environment":"code","path":"code","project":{{"access_token":null,"created_at":null,"git_username":null,"gitlab_host":null,"gitlab_project_id":"1","gitlab_token":"{self.test_token}","gitlab_url":"https://gitlab.comwork.io","gitlab_username":"amirghedira","id":1,"name":"test_project","namespace_id":null,"type":"vm","url":"https://gitlab.comwork.io/dynamic/test_project","user":null,"user_id":1,"userid":null}}}}')

    @patch('utils.dynamic_name.generate_hashed_name', side_effect = lambda p: ("aabbcc", p, "test-aabbcc"))
    @patch('entities.User.User.getUserByEmail')
    @patch('entities.Environment.Environment.getByPath')
    @patch('controllers.admin.admin_instance.get_project_quietly', side_effect = lambda e: {'id': 1})
    @patch('controllers.admin.admin_instance.get_user_project_by_id')
    @patch('controllers.admin.admin_instance.refresh_project_credentials')
    @patch('controllers.admin.admin_instance.register_instance')
    @patch('controllers.admin.admin_instance.create_instance', side_effect = lambda provider, ami_image, instance_id, user_email, instance_name, hashed_instance_name, environment, instance_region, instance_zone, generate_dns, gitlab_project, user_project, instance_type, debug, centralized, root_dns_zone, db : "")
    @patch('controllers.admin.admin_instance.get_gitlab_project_playbooks', side_effect = lambda x, y, z: [])
    @patch('controllers.admin.admin_instance.check_exist_instance', side_effect = lambda userid, instance_name, db: False)
    @patch('utils.common.generate_hash_password', side_effect = lambda p: p)
    def test_admin_create_instance(self, generate_hash_password, check_exist_instance, get_gitlab_project_playbooks, create_instance, register_instance, get_user_project_by_id, refresh_project_credentials, get_gitlab_project, getByPath, getUserByEmail, generate_hashed_name):
        # Given
        from controllers.admin.admin_instance import admin_add_instance
        from entities.Environment import Environment
        from entities.Instance import Instance
        from entities.Project import Project
        from entities.User import User
        from schemas.Instance import InstanceProvisionSchema

        target_user = User()
        target_user.email = "username@gmail.com"
        target_user.id = 1
        target_user.enabled_features = {}
        target_user.enabled_features = {}
        getUserByEmail.return_value = target_user
        
        get_gitlab_project.return_value = {
            "id": 1, 
            "name": "test_project",
            "gitlab_url": "https://gitlab.comwork.io/dynamic/test_project",
            "userid": "1",
            "gitlab_host": "https://gitlab.comwork.io", 
            "access_token": "testingTOKEN", 
            "namespace_id": "1"
        }
        
        project = Project()
        project.name = "test_project"
        project.url = "https://gitlab.comwork.io/dynamic/test_project"
        project.userid = 1
        project.gitlab_host = "https://gitlab.comwork.io"
        project.git_username = "amirghedira"
        project.access_token = self.test_access_token
        project.namespace_id = "1"
        project.id = 1
        get_user_project_by_id.return_value = project
        refresh_project_credentials.return_value = project

        environment = Environment()
        environment.name = "code"
        environment.path = "code"
        environment.description = "code environment"
        environment.is_private = False
        environment.logo_url = "https://whatever.com/logo.png"
        environment.environment_template = ""
        environment.doc_template = ""
        environment.roles = "code"
        environment.subdomains = "comwork.cloud"
        environment.id = 1
        getByPath.return_value = environment
        
        instance_id = 1
        hash, name = ("aabbcc", "test-aabbcc")
        generate_hashed_name.return_value = hash, name
        new_instance = Instance()
        new_instance.hash = hash
        new_instance.name = name
        new_instance.type = "DEV1-S"
        new_instance.provider = "scaleway"
        new_instance.region = "fr-par"
        new_instance.zone = "1"
        new_instance.status = "deleted"
        new_instance.root_dns_zone = "comwork.cloud"
        new_instance.user_id = 1
        new_instance.id = instance_id
        new_instance.environment = environment
        new_instance.project = project
        new_instance.is_protected = False
        register_instance.return_value = new_instance

        payload = InstanceProvisionSchema(
            name = "test",
            email = "test@gmail.com",
            project_id = "1",
            project_name = "test_project",
            project_url = "https://gitlab.comwork.io/dynamic/test_project",
            debug = "true",
            type = "DEV1-S",
            root_dns_zone = "comwork.cloud",
            args = {}
        )

        # When
        result = admin_add_instance(test_current_user, payload, "scaleway", "fr-par", "1", "code", mock_db, mock_bt)
        response_status_code = result.__dict__['status_code']
       
        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), '{"created_at":null,"environment_id":null,"hash":"aabbcc","id":1,"ip_address":null,"is_protected":false,"modification_date":null,"name":"test-aabbcc","project_id":null,"provider":"scaleway","region":"fr-par","root_dns_zone":"comwork.cloud","status":"ok","type":"DEV1-S","user":null,"user_id":1,"zone":"1","environment":"code","path":"code","gitlab_project":"https://gitlab.comwork.io/dynamic/test_project"}')
