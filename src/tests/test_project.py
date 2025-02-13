from unittest import TestCase
from unittest.mock import Mock, patch
from uuid import uuid4
from fastapi.responses import JSONResponse

test_current_user = Mock()
mock_db = Mock()

def get_test_token():
    """Generate a temporary token for testing purposes"""
    return f"test_{uuid4().hex[:10]}"

class TestProject(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestProject, self).__init__(*args, **kwargs)
        self.test_token = get_test_token()
        
    @patch('entities.Access.Access.getUserAccessesByType', side_effect = lambda x, y, z: [])
    @patch('entities.Project.Project.findProjects', side_effect = lambda x, y: [])
    @patch('entities.Project.Project.getUserProjectsByType', side_effect = lambda x, y, z : [])
    @patch('entities.Instance.Instance.getActiveUserInstances', side_effect = lambda x, y : [])
    def test_get_projects(self, getActiveUserInstances, getUserProjectsByType, findProjects, getUserAccessesByType):
        # Given
        from controllers.project import get_projects
        getUserProjectsByType.return_value = []
        # When
        result = get_projects(test_current_user, "all", mock_db)
        response_status_code = result.__dict__['status_code']

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), "[]")

    @patch('entities.Project.Project.save')
    @patch('middleware.auth_guard.is_mock_test', side_effect = lambda: True)
    @patch('middleware.auth_guard.get_current_active_user', side_effect = lambda x: test_current_user)
    @patch('utils.common.generate_hash_password', side_effect = lambda p: p)
    @patch('utils.gitlab.create_gitlab_project')
    def test_add_project(self, create_gitlab_project_mock, generate_hash_password, get_current_active_user, is_mock_test, project_save_mock):
        # Given
        from entities.User import User
        from controllers.project import add_project
        from entities.Project import Project
        from schemas.Project import ProjectSchema

        target_user = User()
        target_user.email = "username@email.com"
        target_user.id = 1

        project_id = 1
        project_name = "test_project"
        new_project = Project()
        new_project.id = project_id
        new_project.name = project_name
        new_project.url = "https://gitlab.comwork.io/dynamic/test_project"
        new_project.user_id = target_user.id
        new_project.gitlab_url = "https://gitlab.comwork.io"
        new_project.gitlab_username = "amirghedira"
        new_project.gitlab_token = self.test_token
        new_project.gitlab_project_id = "1"
        new_project.type = "vm"
        create_gitlab_project_mock.return_value = new_project

        payload = ProjectSchema(
            name = project_name,
            type = "vm",
            host = "https://gitlab.comwork.io",
            token = self.test_token,
            git_username = "amirghedira",
            git_useremail = "username@email.com",
            namespace = "dynamic"
        )

        # When
        result = add_project(test_current_user, payload, mock_db)
        response_status_code = result.__dict__['status_code']

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 201)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), f'{{"access_token":null,"created_at":null,"git_username":null,"gitlab_host":null,"gitlab_project_id":"1","gitlab_token":"{self.test_token}","gitlab_url":"https://gitlab.comwork.io","gitlab_username":"amirghedira","id":1,"instances":[],"name":"test_project","namespace_id":null,"type":"vm","url":"https://gitlab.comwork.io/dynamic/test_project","user":null,"user_id":1,"userid":null}}')

    @patch('entities.Project.Project.getUserProject')
    @patch('utils.gitlab.get_gitlab_project_tree', side_effect = lambda x, y, z: [])
    @patch('entities.User.User.getUserById') 
    def test_get_project(self, getUserById, get_gitlab_project_playbooks, getUserProject):
        # Given
        from controllers.project import get_project
        from entities.Project import Project
        from entities.User import User

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
        project.type = "vm"
        getUserProject.return_value = project

        userId = 1
        enabled_features = {
            "daasapi": True,
            "k8sapi": True
        }
        test_user = User(id= userId, enabled_features=enabled_features)
        getUserById.return_value = test_user

        # When
        result = get_project(test_user, project_id, mock_db)
        response_status_code = result.__dict__['status_code']

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), f'{{"access_token":null,"created_at":null,"git_username":null,"gitlab_host":null,"gitlab_project_id":"1","gitlab_token":"{self.test_token}","gitlab_url":"https://gitlab.comwork.io","gitlab_username":"amirghedira","id":1,"instances":[],"name":"test_project","namespace_id":null,"type":"vm","url":"https://gitlab.comwork.io/dynamic/test_project","user":null,"user_id":1,"userid":null,"playbooks":[]}}')

    @patch('controllers.project.delete_gitlab_project', side_effect = lambda x, y, z : "" )
    @patch('entities.Project.Project.deleteOne', side_effect = lambda x, y : "" )
    @patch('entities.Project.Project.getUserProject')
    @patch('entities.Instance.Instance.getAllActiveInstancesByProject', side_effect = lambda x, y : [])
    @patch('entities.User.User.getUserById') 
    def test_delete_project(self, getUserById, getAllActiveInstancesByProject, getUserProject, deleteOne, delete_gitlab_project):
        # Given
        from controllers.project import delete_project
        from entities.Project import Project
        from entities.User import User

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
        getUserProject.return_value = project

        userId = 1
        enabled_features = {
            "daasapi": True,
            "k8sapi": True
        }
        test_user = User(id= userId, enabled_features=enabled_features)
        getUserById.return_value = test_user

        # When
        result = delete_project(test_user, project_id, mock_db)
        response_status_code = result.__dict__['status_code']

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(response_status_code, 200)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.body.decode(), '{"status":"ok","message":"project successfully deleted","i18n_code":"project_deleted"}')
