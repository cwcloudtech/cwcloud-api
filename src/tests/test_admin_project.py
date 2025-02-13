from unittest import TestCase
from unittest.mock import Mock, patch
from uuid import uuid4
from fastapi.responses import JSONResponse

test_current_user = Mock()
mock_db = Mock()

def get_test_token():
    """Generate a temporary token for testing purposes"""
    return f"test_{uuid4().hex[:10]}"

class TestAdminProject(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestAdminProject, self).__init__(*args, **kwargs)
        self.test_token = get_test_token()

    @patch('entities.Project.Project.getAllProjects', side_effect = lambda x: [])
    @patch('entities.Instance.Instance.getAllInstances', side_effect = lambda x: [])
    def test_get_admin_projects(self, getAllProjects, getAllInstances):
        # Given
        from controllers.admin.admin_project import admin_get_projects

        # When
        result = admin_get_projects(mock_db)
        response_status_code = result.__dict__['status_code']

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), "[]")

    @patch('entities.Project.Project.getProjectById')
    @patch('utils.gitlab.get_gitlab_project_tree', side_effect = lambda x, y, z: [])
    def test_get_admin_project(self, get_gitlab_project_playbooks, getProjectById):
        # Given
        from controllers.admin.admin_project import admin_get_project
        from entities.Project import Project
        project_id = 1
        new_project = Project()
        new_project.id = project_id
        new_project.name = "test_project"
        new_project.url = "https://gitlab.comwork.io/dynamic/test_project"
        new_project.user_id = 1
        new_project.gitlab_url = "https://gitlab.comwork.io"
        new_project.gitlab_username = "amirghedira"
        new_project.gitlab_token = self.test_token
        new_project.gitlab_project_id = "1"
        new_project.type = "vm"
        getProjectById.return_value = new_project

        # When
        result = admin_get_project(project_id, mock_db)
        response_status_code = result.__dict__['status_code']
    
        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.maxDiff = None
        import json
        actual_json = json.loads(result.body.decode())
        expected_json = {
            "access_token": None,
            "created_at": None,
            "git_username": None,
            "gitlab_host": None,
            "gitlab_project_id": "1",
            "gitlab_token": self.test_token,
            "gitlab_url": "https://gitlab.comwork.io",
            "gitlab_username": "amirghedira",
            "id": 1,
            "instances": [],
            "name": "test_project",
            "namespace_id": None,
            "playbooks": [],
            "type": "vm",
            "url": "https://gitlab.comwork.io/dynamic/test_project",
            "user": None,
            "user_id": 1,
            "userid": None
        }
        self.assertEqual(actual_json, expected_json)

    @patch('entities.User.User.getUserByEmail')
    @patch('entities.Project.Project.save')
    @patch('middleware.auth_guard.is_mock_test', side_effect = lambda: True)
    @patch('middleware.auth_guard.get_current_active_user', side_effect = lambda: test_current_user)
    @patch('utils.common.generate_hash_password', side_effect = lambda p: p)
    @patch('utils.gitlab.create_gitlab_project')
    def test_add_admin_projects(self, create_gitlab_project_mock, generate_hash_password, get_current_active_user, is_mock_test, project_save_mock, mock_get_user_by_mail):
        # Given
        from entities.User import User
        from controllers.admin.admin_project import admin_add_project
        from entities.Project import Project
        from schemas.Project import ProjectAdminSchema
        target_user_project = User()
        target_user_project.email = "username@email.com"
        target_user_project.id = 1
        project_id = 1
        mock_get_user_by_mail.return_value = target_user_project

        new_project = Project()
        new_project.id = project_id
        new_project.name = "test_project"
        new_project.url = "https://gitlab.comwork.io/dynamic/test_project"
        new_project.user_id = 1
        new_project.gitlab_url = "https://gitlab.comwork.io"
        new_project.gitlab_username = "amirghedira"
        new_project.gitlab_token = self.test_token
        new_project.gitlab_project_id = "1"
        new_project.type = "vm"
        create_gitlab_project_mock.return_value = new_project

        payload = ProjectAdminSchema(
            name = "test_project",
            email = "username@email.com",
            type = "vm",
            host = "default_host",
            token = self.test_token,
            git_username = "default_git_username",
            git_useremail = "default_git_useremail",
            namespace = "default_namespace"
        )

        # When
        result = admin_add_project(payload, mock_db)
        response_status_code = result.__dict__['status_code']

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 201)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), f'{{"access_token":null,"created_at":null,"git_username":null,"gitlab_host":null,"gitlab_project_id":"1","gitlab_token":"{self.test_token}","gitlab_url":"https://gitlab.comwork.io","gitlab_username":"amirghedira","id":1,"instances":[],"name":"test_project","namespace_id":null,"type":"vm","url":"https://gitlab.comwork.io/dynamic/test_project","user":null,"user_id":1,"userid":null}}')

    @patch('controllers.admin.admin_project.delete_gitlab_project', side_effect = lambda x, y, z : "" )
    @patch('entities.Project.Project.deleteOne')
    @patch('entities.Project.Project.getProjectById')
    @patch('entities.Instance.Instance.getAllActiveInstancesByProject')
    def test_admin_delete_project(self, getAllActiveInstancesByProject, getProjectById, deleteOne, delete_gitlab_project):
        # Given
        from controllers.admin.admin_project import admin_remove_project
        from entities.Project import Project
        project_id = 1
        project = Project()
        project.id = project_id
        project.name = "test_project"
        project.url = "https://gitlab.comwork.io/dynamic/test_project"
        project.user_id = 1
        project.gitlab_url = "https://gitlab.comwork.io"
        project.gitlab_username = "amirghedira"
        project.gitlab_token = self.test_token
        project.gitlab_project_id = "1"
        getProjectById.return_value = project

        # When
        result = admin_remove_project(project_id, mock_db)
        response_status_code = result.__dict__['status_code']
       
        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), '{"status":"ok","message":"project successfully deleted","i18n_code":"project_deleted"}')
