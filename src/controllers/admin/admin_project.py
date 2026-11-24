import json

from urllib.error import HTTPError
from urllib.parse import unquote
from fastapi.responses import JSONResponse

from entities.Project import Project
from entities.Instance import Instance

from utils.common import is_numeric, is_empty
from utils.encoder import AlchemyEncoder
from utils.gitlab import  create_gitlab_project, delete_gitlab_project, get_gitlab_project_playbooks, attach_default_gitlab_project_to_user, detach_user_gitlab_project
from utils.observability.cid import get_current_cid

def admin_transfer_project (project_id, payload, db):
    try:
        email = payload.email
        if not is_numeric(project_id):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Invalid project id',
                'cid': get_current_cid()
            }, status_code = 400)

        project = Project.getProjectById(project_id, db)
        if not project:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found', 
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        from entities.User import User
        user = User.getUserByEmail(email, db)
        if not user:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'user not found', 
                'i18n_code': 'user_not_found',
                'cid': get_current_cid()
            }, status_code = 409)

        original_project_user = User.getUserById(project.id, db)
        Project.updateOwner(project.id, user.id, db)
        attach_default_gitlab_project_to_user(project.id, user.email)
        detach_user_gitlab_project(project.id, original_project_user)

        Instance.updateProjectInstancesOwner(project.id, user.id, db)
        projectsInstances = Instance.getAllActiveInstancesByProject(project.id, db)
        projectInstancesIds = [instance.id for instance in projectsInstances]

        from entities.Access import Access
        Access.updateObjectsAccessesOwner("instance", projectInstancesIds, user.id, db)
        Access.updateObjectAccessesOwner("project", project.id, user.id, db)

        return JSONResponse(content = {
            'status': 'ok',
            'message': 'successfully transfered project'
        }, status_code = 200)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)

def admin_add_project(payload, db):
    try:
        user_email = payload.email
        project_name = payload.name
        host = payload.host
        token = payload.token
        git_username = payload.git_username
        namespace = payload.namespace
        project_type = payload.type

        from entities.User import User
        target_user = User.getUserByEmail(user_email, db)
        if not target_user:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'user not found', 
                'i18n_code': 'user_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        if is_empty(project_type):
            project_type = 'vm'
        project = create_gitlab_project(project_name, target_user.id, target_user.email, host, git_username, token, namespace, project_type, db)
        projectJson = json.loads(json.dumps(project, cls = AlchemyEncoder))
        return JSONResponse(content = projectJson, status_code = 201)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)

def admin_get_projects(db):
    projects = Project.getAllProjects(db)
    projectsJson = json.loads(json.dumps(projects, cls = AlchemyEncoder))

    user_instances = Instance.getAllInstances(db)
    user_instancesJson = json.loads(json.dumps(user_instances, cls = AlchemyEncoder))
    populatedInstancesProjects = [{**project, "instances": [instance for instance in user_instancesJson if instance["project_id"] == project["id"] ]} for project in projectsJson]
    return JSONResponse(content = populatedInstancesProjects, status_code = 200)

def admin_get_project(project_id, db):
    try:
        if not is_numeric(project_id):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Invalid project id',
                'cid': get_current_cid()
            }, status_code = 400)

        project = Project.getProjectById(project_id, db)
        if not project:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found', 
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        playbooks = get_gitlab_project_playbooks(project.id, project.gitlab_host, project.access_token)
        projectJson = json.loads(json.dumps(project, cls = AlchemyEncoder))
        instancesJson = json.loads(json.dumps(project.instances, cls = AlchemyEncoder))
        userJson = json.loads(json.dumps(project.user, cls = AlchemyEncoder))
        filteredInstances = [instance for instance in instancesJson if instance["status"] != "deleted"]
        project_response = {**projectJson, "playbooks": playbooks, "instances": filteredInstances, "user": userJson}
        return JSONResponse(content = project_response, status_code = 200)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)

def admin_remove_project(project_id, db):
    try:
        if not is_numeric(project_id):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Invalid project id',
                'cid': get_current_cid()
            }, status_code = 400)

        project = Project.getProjectById(project_id, db)
        if not project:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found', 
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        project_instances = Instance.getAllActiveInstancesByProject(project_id, db)
        if len(project_instances) > 0:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project still holds active instances', 
                'i18n_code': 'project_hold_active_instances',
                'cid': get_current_cid()
            }, status_code = 400)

        delete_gitlab_project(project_id, project.gitlab_host, project.access_token)
        Project.deleteOne(project_id, db)
        return JSONResponse(content = {
            'status': 'ok',
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

def admin_get_project_by_name(project_name, db):
    try:
        project = Project.getProjectByName(project_name, db)
        if not project:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found', 
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        playbooks = get_gitlab_project_playbooks(project.id, project.gitlab_host, project.access_token)
        projectJson = json.loads(json.dumps(project, cls = AlchemyEncoder))
        instancesJson = json.loads(json.dumps(project.instances, cls = AlchemyEncoder))
        filteredInstances = [instance for instance in instancesJson if instance["status"] != "deleted"]
        project_response = {**projectJson, "playbooks": playbooks, "instances": filteredInstances}
        return JSONResponse(content = project_response, status_code = 200)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        } , status_code = e.code)

def admin_remove_project_by_name(project_name, db):
    try:
        project = Project.getProjectByName(project_name, db)
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

        delete_gitlab_project(project.id, project.gitlab_host, project.access_token)
        Project.deleteOne(project.id, db)
        return JSONResponse(content = {
            'status': 'ok',
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

def admin_get_project_by_url(project_url, db):
    try:
        project = Project.getProjectByUrl(unquote(project_url), db)
        if not project:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found', 
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        playbooks = get_gitlab_project_playbooks(project.id, project.gitlab_host, project.access_token)
        projectJson = json.loads(json.dumps(project, cls = AlchemyEncoder))
        instancesJson = json.loads(json.dumps(project.instances, cls = AlchemyEncoder))
        filteredInstances = [instance for instance in instancesJson if instance["status"] != "deleted"]
        project_response = {**projectJson, "playbooks": playbooks, "instances": filteredInstances}
        return JSONResponse(content = project_response, status_code = 200)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg, 
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)

def admin_remove_project_by_url(project_url, db):
    try:
        project = Project.getProjectByUrl(unquote(project_url), db)
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

        delete_gitlab_project(project.id, project.gitlab_host, project.access_token)
        Project.deleteOne(project.id, db)
        return JSONResponse(content = {
            'status': 'ok',
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

def admin_get_user_projects(user_id, db):
    userRegionProjects = Project.getUserProjects(user_id, db)
    userRegionProjectsJson = json.loads(json.dumps(userRegionProjects, cls = AlchemyEncoder))
    return JSONResponse(content = userRegionProjectsJson, status_code = 200)
