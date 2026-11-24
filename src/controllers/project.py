import json

from urllib.error import HTTPError

from fastapi.responses import JSONResponse
from fastapi import status
from entities.Project import Project
from entities.Instance import Instance
from entities.Access import Access
from entities.kubernetes.Deployment import Deployment
from entities.Environment import Environment
from entities.User import User
from exceptions.CwHTTPException import CwHTTPException
from utils.common import is_empty, is_numeric, is_true
from utils.encoder import AlchemyEncoder
from utils.flag import is_flag_disabled
from utils.gitlab import create_gitlab_project, delete_gitlab_project, get_gitlab_project_playbooks, attach_default_gitlab_project_to_user, detach_user_gitlab_project
from utils.observability.cid import get_current_cid

def check_permissions(current_user, project, db):
    user = User.getUserById(current_user.id, db)
    if is_true(user.is_admin):
        return
    if project.type == "vm" and is_flag_disabled(user.enabled_features, "daasapi"):
        raise CwHTTPException(
            message={
                'status': 'ko',
                'error': 'permission denied',
                'i18n_code': 'not_daasapi',
                'cid': get_current_cid()
            },
            status_code=status.HTTP_403_FORBIDDEN
        )
    if project.type == "k8s" and is_flag_disabled(user.enabled_features, "k8sapi"):
        raise CwHTTPException(
            message={
                'status': 'ko',
                'error': 'permission denied',
                'i18n_code': 'not_k8sapi',
                'cid': get_current_cid()
            },
            status_code=status.HTTP_403_FORBIDDEN
        )

def transfer_project(current_user, payload, projectId, db):
    try:
        if not is_numeric(projectId):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Invalid project id',
                'i18n_code': 'invalid_numeric_id',
                'cid': get_current_cid()
            }, status_code = 400)

        project = Project.getUserProject(projectId, current_user.id, db)
        if not project:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found', 
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        from entities.User import User
        user = User.getUserByEmail(payload.email, db)
        if not user:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'user not found', 
                'i18n_code': 'user_not_found',
                'cid': get_current_cid()
            }, status_code = 409)

        check_permissions(current_user, project, db)

        Project.updateOwner(project.id, user.id, db)
        attach_default_gitlab_project_to_user(project.id, user.email)
        detach_user_gitlab_project(project.id, current_user.email)

        Instance.updateProjectInstancesOwner(project.id, user.id, db)
        projectsInstances = Instance.getAllActiveInstancesByProject(project.id, db)
        projectInstancesIds = [instance.id for instance in projectsInstances]

        Access.updateObjectsAccessesOwner("instance", projectInstancesIds, user.id, db)
        Access.updateObjectAccessesOwner("project", project.id, user.id, db)

        return JSONResponse(content = {
            'status': 'ok',
            'message': 'successfully transfered project',
            'i18n_code': 'project_transfered',
            'cid': get_current_cid()
        }, status_code = 200)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)

def add_project(current_user, payload, db):
    try:
        project_name = payload.name
        if is_empty(project_name):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project name is missing', 
                'i18n_code': 'project_name_missing',
                'cid': get_current_cid()
            }, status_code = 400)
        if not project_name or project_name == "":
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project name is missing', 
                'i18n_code': 'project_name_missing',
                'cid': get_current_cid()
            }, status_code = 400)

        project_type = payload.type
        if is_empty(project_type):
            project_type = "vm"
        project = create_gitlab_project(
            project_name,
            current_user.id,
            current_user.email,
            payload.host,
            payload.git_username,
            payload.token,
            payload.namespace,
            project_type,
            db
        )
        projectJson = json.loads(json.dumps(project, cls = AlchemyEncoder))
        return JSONResponse(content = projectJson, status_code = 201)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)

def get_projects(current_user, type, db):
    projects = []
    projects = Project.getUserProjectsByType(current_user.id, type, db)
    other_projects_access = Access.getUserAccessesByType(current_user.id, "project", db)
    other_project_ids = [access.object_id for access in other_projects_access]
    other_projects = Project.findProjects(other_project_ids, db)
    projects.extend(other_projects)
    projectsJson = json.loads(json.dumps(projects, cls = AlchemyEncoder))
    user_instances = Instance.getActiveUserInstances(current_user.id, db)
    user_instancesJson = json.loads(json.dumps(user_instances, cls = AlchemyEncoder))

    for project in projectsJson:
        deployment = Deployment.getFirstByProject(project["id"], db)
        project["environment"] = None
        if is_true(deployment):
            environemnt = Environment.getById(deployment.env_id, db)
            project["environment"] = {
                "id": environemnt.id,
                "name": environemnt.name,
            }
    populatedProjects = [
        {
            **project,
            "instances": [instance for instance in user_instancesJson if instance["project_id"] == project["id"] ]
        } for project in projectsJson
    ]
    
    return JSONResponse(content = populatedProjects, status_code = 200)

def get_project(current_user, projectId, db):
    try:
        if not is_numeric(projectId):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Invalid project id', 
                'i18n_code': 'invalid_numeric_id',
                'cid': get_current_cid()
            }, status_code = 400)

        project = Project.getUserProject(projectId, current_user.id, db)
        if not project:
            access = Access.getUserAccessToObject(current_user.id, "project", projectId, db)
            if not access:
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': 'project not found', 
                    'i18n_code': 'project_not_found',
                    'cid': get_current_cid()
                }, status_code = 404)
            project = Project.getProjectById(access.object_id, db)
        
        check_permissions(current_user, project, db)

        projectJson = json.loads(json.dumps(project, cls = AlchemyEncoder))

        if project.type == "vm":
            playbooks = get_gitlab_project_playbooks(project.id, project.gitlab_host, project.access_token)
            instancesJson = json.loads(json.dumps(project.instances, cls = AlchemyEncoder))
            filteredInstances = [instance for instance in instancesJson if instance['status'] != "deleted"]
            project_response = {**projectJson, "playbooks": playbooks, "instances": filteredInstances}
        else:
            deployments = Deployment.getAllByProject(project.id, db)
            deploymentsJson = json.loads(json.dumps(deployments, cls = AlchemyEncoder))
            project_response = {**projectJson, "deployments": deploymentsJson}

        return JSONResponse(content = project_response, status_code = 200)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)

def delete_project(current_user, projectId, db):
    try:
        if not is_numeric(projectId):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Invalid project id', 
                'i18n_code': 'invalid_numeric_id',
                'cid': get_current_cid()
            }, status_code = 400)

        project = Project.getUserProject(projectId, current_user.id, db)
        if not project:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found', 
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        project_instances = Instance.getAllActiveInstancesByProject(projectId, db)
        if len(project_instances) > 0:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project still holds active instances', 
                'i18n_code': 'project_hold_active_instances',
                'cid': get_current_cid()
            }, status_code = 400)

        check_permissions(current_user, project, db)
        delete_gitlab_project(projectId, project.gitlab_host, project.access_token)
        Project.deleteOne(projectId, db)

        return JSONResponse(content = {
            'status' : 'ok',
            'message' : 'project successfully deleted', 
            'i18n_code': 'project_deleted'
        }, status_code = 200)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)

def get_project_by_name(current_user, project_name, db):
    try:
        project = Project.getUserProjectByName(project_name, current_user.id, db)
        if not project:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found', 
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        check_permissions(current_user, project, db)
        playbooks = get_gitlab_project_playbooks(project.id, project.gitlab_host, project.access_token)
        projectJson = json.loads(json.dumps(project, cls = AlchemyEncoder))
        instancesJson = json.loads(json.dumps(project.instances, cls = AlchemyEncoder))
        filteredInstances = [instance for instance in instancesJson if instance['status'] != "deleted"]
        project_response = {**projectJson, "playbooks": playbooks, "instances": filteredInstances}

        return JSONResponse(content = project_response, status_code = 200)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)

def delete_project_by_name(current_user, project_name, db):
    try:
        project = Project.getUserProjectByName(project_name, current_user.id, db)
        if not project:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found', 
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        project_instances = Instance.getAllActiveInstancesByProject(project.id, db)
        if len(project_instances) > 0:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project still holds active instances', 
                'i18n_code': 'project_hold_active_instances',
                'cid': get_current_cid()
            }, status_code = 400)

        check_permissions(current_user, project, db)
        delete_gitlab_project(project.id, project.gitlab_host, project.access_token)
        Project.deleteOne(project.id, db)

        return JSONResponse(content = {
             'status' : 'ok',
            'message' : 'project successfully deleted', 
            'i18n_code': 'project_deleted'
        }, status_code = 200)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)

def get_project_by_url(current_user, project_url, db):
    try:
        project = Project.getUserProjectByUrl(project_url, current_user.id, db)
        if not project:
            return JSONResponse(content = {
                'status': 'ko', 
                'error': 'project not found', 
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        check_permissions(current_user, project, db)
        playbooks = get_gitlab_project_playbooks(project.id, project.gitlab_host, project.access_token)
        projectJson = json.loads(json.dumps(project, cls = AlchemyEncoder))
        instancesJson = json.loads(json.dumps(project.instances, cls = AlchemyEncoder))
        filteredInstances = [instance for instance in instancesJson if instance['status'] != 'deleted']
        project_response = {**projectJson, "playbooks": playbooks, "instances": filteredInstances}

        return JSONResponse(content = project_response, status_code = 200)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)

def delete_project_by_url(current_user, project_url, db):
    try:
        project = Project.getUserProjectByUrl(project_url, current_user.id, db)
        if not project:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found', 
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        project_instances = Instance.getAllActiveInstancesByProject(project.id, db)
        if len(project_instances) > 0:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project still holds active instances', 
                'i18n_code': 'project_hold_active_instances',
                'cid': get_current_cid()
            }, status_code = 400)

        check_permissions(current_user, project, db)
        delete_gitlab_project(project.id, project.gitlab_host, project.access_token)
        Project.deleteOne(project.id, db)

        return JSONResponse(content = {
            'status' : 'ok',
            'message' : 'project successfully deleted', 
            'i18n_code': 'project_deleted'
        }, status_code = 200)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)
