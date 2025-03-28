import json

from urllib.error import HTTPError
from pulumi import automation as auto
from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse

from utils.common import is_boolean, is_empty, is_false, is_not_empty, is_numeric, is_true
from utils.flag import is_flag_disabled
from utils.dns_zones import get_dns_zones
from utils.domain import is_not_subdomain_valid
from utils.gitlab import get_gitlab_project, get_gitlab_project_playbooks, get_project_quietly, get_user_project_by_id, get_user_project_by_name, get_user_project_by_url, is_http_error_fetching_project, is_not_project_found_in_gitlab, refresh_project_credentials
from utils.dynamic_name import generate_hashed_name
from utils.encoder import AlchemyEncoder
from utils.images import get_os_image
from utils.logger import log_msg
from utils.dynamic_name import rehash_dynamic_name
from utils.instance import check_exist_instance, generic_remove_instance, get_server_state, get_virtual_machine, reregister_instance, register_instance, create_instance, update_instance_status, check_instance_name_validity
from utils.provider import exist_provider, get_provider_infos, get_provider_available_instances_by_region_zone
from utils.zone_utils import exists_zone
from utils.observability.cid import get_current_cid

def get_instance(current_user, provider, region, instance_id, db):
    if not exist_provider(provider):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'provider does not exist',
            'i18n_code': 'provider_not_exist',
            'cid': get_current_cid()
        }, status_code = 404)

    if not is_numeric(instance_id):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Invalid instance id',
            'i18n_code': "invalid_instance_id",
            'cid': get_current_cid()
        }, status_code = 400)

    from entities.Instance import Instance
    userInstance = Instance.findUserInstance(current_user.id, provider, region, instance_id, db)
    if not userInstance:
        from entities.Access import Access
        access = Access.getUserAccessToObject(current_user.id, "instance", instance_id, db)
        if not access:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Instance not found',
                'i18n_code': "instance_not_found",
                'cid': get_current_cid()
            }, status_code = 404)

        userInstance = Instance.findInstance(provider, region, access.object_id, db)

    dumpedInstance = json.loads(json.dumps(userInstance, cls = AlchemyEncoder))
    dumpedProject = json.loads(json.dumps(userInstance.project, cls = AlchemyEncoder))
    instanceJson = {
        **dumpedInstance,
        "environment": userInstance.environment.name,
        "path": userInstance.environment.path,
        "project": {**dumpedProject}
    }

    return JSONResponse(content = instanceJson, status_code = 200)

def remove_instance(current_user, provider, region, instance_id, db, bt: BackgroundTasks):
    if not exist_provider(provider):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'provider does not exist',
            'i18n_code': 'provider_not_exist',
            'cid': get_current_cid()
        }, status_code = 404)

    if not is_numeric(instance_id):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Invalid instance id',
            'i18n_code': 'invalid_numeric_id',
            'cid': get_current_cid()
        }, status_code = 400)

    from entities.Instance import Instance
    user_instance = Instance.findUserInstance(current_user.id, provider, region, instance_id, db)
    if not user_instance:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Instance not found',
            'i18n_code': "instance_not_found",
            'cid': get_current_cid()
        }, status_code = 404)
    if is_true(user_instance.is_protected):
        return JSONResponse(content = {
            'status': 'ko',
            'error': "You can't remove a protected instance",
            'i18n_code': 'can_not_remove_protected_instance',
            'cid': get_current_cid()
        }, status_code = 400)

    result_remove = generic_remove_instance(user_instance, db, bt)
    if is_false(result_remove['status']):
        return JSONResponse(content = {
            'status': 'ko',
            'error': result_remove["error"],
            'i18n_code': result_remove["i18n_code"],
            'cid': get_current_cid()
        }, status_code = result_remove["http_code"])

    return JSONResponse(content = result_remove["message"], status_code = result_remove["http_code"])

def update_instance(current_user, payload, provider, region, instance_id, db):
    action = payload.status
    is_protected = payload.is_protected

    if not exist_provider(provider):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'provider does not exist',
            'i18n_code': 'provider_not_exist',
            'cid': get_current_cid()
        }, status_code = 404)

    if not is_numeric(instance_id):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Invalid instance id',
            'i18n_code': 'invalid_instance_id',
            'cid': get_current_cid()
        }, status_code = 400)

    from entities.Instance import Instance
    userInstance = Instance.findUserInstance(current_user.id, provider, region, instance_id, db)
    if not userInstance:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Instance not found',
            'i18n_code': 'instance_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    server = get_virtual_machine(userInstance.provider, userInstance.region, userInstance.zone, rehash_dynamic_name(userInstance.name, userInstance.hash))
    if not server:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Instance not found',
            'i18n_code': 'instance_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    target_server_id = server["id"]
    possible_actions = ["poweroff", "poweron", "reboot"]
    if is_not_empty(action):
        if action not in possible_actions:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'action doesnt exist',
                'i18n_code': 'action_not_exist',
                'cid': get_current_cid()
            }, status_code = 400)

        server_state = get_server_state(userInstance.provider, server)

        if action == "poweroff":
            if server_state == "stopped":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': 'Instance already stopped',
                    'i18n_code': 'instance_stopped',
                    'cid': get_current_cid()
                }, status_code = 400)

            if server_state == "rebooting":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': "You can't stop the Instance while rebooting",
                    'i18n_code': 'can_not_stop_instance_while_reboot',
                    'cid': get_current_cid()
                }, status_code = 400)

            if server_state == "starting":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': "You can't stop the Instance while starting",
                    'i18n_code': 'can_not_stop_instance_while_start',
                    'cid': get_current_cid()
                }, status_code = 400)

            if server_state == "stopping":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': 'Instance already stopping',
                    'i18n_code': 'instance_stopping',
                    'cid': get_current_cid()
                }, status_code = 400)

        if action == "poweron":
            if server_state == "running":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': 'Instance already running',
                    'i18n_code': 'instance_running',
                    'cid': get_current_cid()
                }, status_code = 400)

            if server_state == "rebooting":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': "You can't start the Instance while rebooting",
                    'i18n_code': 'can_not_start_instance_while_reboot',
                    'cid': get_current_cid()
                }, status_code = 400)

            if server_state == "starting":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': 'Instance already starting',
                    'i18n_code': 'instance_starting',
                    'cid': get_current_cid()
                }, status_code = 400)

            if server_state == "stopping":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': "You can't start the Instance while stopping",
                    'i18n_code': 'can_not_start_instance_while_stop',
                    'cid': get_current_cid()
                }, status_code = 400)

        if action == "reboot":
            if server_state == "stopped":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': "You can't reboot the Instance when it is stopped",
                    'i18n_code': 'can_not_reboot_instance_while_stop',
                    'cid': get_current_cid()
                }, status_code = 400)

            if server_state == "rebooting":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': 'Instance already rebooting',
                    'i18n_code': 'instance_rebooting',
                    'cid': get_current_cid()
                }, status_code = 400)

            if server_state == "starting":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': "You can't reboot the Instance while starting",
                    'i18n_code': 'can_not_reboot_instance_while_start',
                    'cid': get_current_cid()
                }, status_code = 400)

            if server_state == "stopping":
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': "You can't reboot the Instance while stopping",
                    'i18n_code': 'can_not_reboot_instance_while_stop',
                    'cid': get_current_cid()
                }, status_code = 400)
            
            if is_true(userInstance.is_protected):
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': "You can't reboot a protected instance",
                    'i18n_code': 'can_not_reboot_protected_instance',
                    'cid': get_current_cid()
                }, status_code = 400)

        if userInstance.status == "active" and action == "activate":
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'instance already active',
                'i18n_code': 'instance_active',
                'cid': get_current_cid()
            }, status_code = 400)

        if action and not action == "":
            update_instance_status(userInstance, target_server_id, action, db)

    if is_boolean(is_protected):
        if is_true(is_protected) and userInstance.is_protected:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Instance already protected',
                'i18n_code': 'instance_already_protected',
                'cid': get_current_cid()
            }, status_code = 400)

        if is_false(is_protected) and not userInstance.is_protected:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Instance already unprotected',
                'i18n_code': 'instance_already_unprotected',
                'cid': get_current_cid()
            }, status_code = 400)

        Instance.updateProtection(userInstance.id, is_protected, db)

    return JSONResponse(content = {
        'status': 'ok',
        'message': 'instance successfully updated',
        'i18n_code': '101'
    }, status_code = 200)

def attach_instance(bt: BackgroundTasks, current_user, provider, region, zone, project_id, payload, db):
    instance_name = payload.name
    instance_type = payload.type
    debug = payload.debug
    generate_dns = "false"
    #? Will only make a sed on the gitlab-runner
    centralized = "false"

    if is_not_subdomain_valid(instance_name):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'The instance name is not valid',
            'i18n_code': 'instance_name_invalid',
            'cid': get_current_cid()
        }, status_code = 400)

    from entities.Instance import Instance
    userInstance = Instance.findUserInstanceByName(current_user.id, instance_name, db)
    if not userInstance:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Instance not found',
            'i18n_code': "instance_not_found",
            'cid': get_current_cid()
        }, status_code = 404)
    if userInstance.status != "deleted":
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Instance already running with this playbook',
            'i18n_code': 'instance_running_with_playbook',
            'cid': get_current_cid()
        }, status_code = 404)

    hash = userInstance.hash
    hashed_instance_name = rehash_dynamic_name(instance_name, hash)
    log_msg("DEBUG", "[instance][attach_instance] hash = {}, hashed_instance_name = {}".format(hash, hashed_instance_name))

    if not exist_provider(provider):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'provider does not exist',
            'i18n_code': 'provider_not_exist',
            'cid': get_current_cid()
        }, status_code = 404)

    exist_project = get_user_project_by_id(project_id, current_user.id, db)
    if is_empty(exist_project):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Project not found',
            'i18n_code': 'project_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    gitlab_project = get_project_quietly(exist_project)
    if is_http_error_fetching_project(gitlab_project):
        return JSONResponse(content= {
            'status': 'ko',
            'error': gitlab_project['reason'],
            'i18n_code': gitlab_project['i18n_code'],
            'cid': get_current_cid()
        }, status_code = gitlab_project['http_code'])
    elif is_not_project_found_in_gitlab(gitlab_project):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'project not found with gitlab',
            'i18n_code':  'project_not_found_with_gitlab',
            'cid': get_current_cid()
        }, status_code = 404)

    exist_project = refresh_project_credentials(db, exist_project, gitlab_project)
    project_playbooks = get_gitlab_project_playbooks(exist_project.id, exist_project.gitlab_host, exist_project.access_token)
    if len(project_playbooks) == 0:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Project has no playbooks',
            'i18n_code': 'project_has_no_playbooks',
            'cid': get_current_cid()
        }, status_code = 400)

    if is_empty(instance_name):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'please specify the playbook you want to attach',
            'i18n_code': 'select_playbook',
            'cid': get_current_cid()
        }, status_code = 400)
    if instance_name not in [name.split("playbook-")[1] for name in project_playbooks]:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'playbook not found',
            'i18n_code': 'playbook_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    if not instance_type or instance_type == "":
        instance_type = get_provider_available_instances_by_region_zone(provider, region, zone)[0]
    else:
        possible_types = get_provider_available_instances_by_region_zone(provider, region, zone)
        if instance_type not in possible_types:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Instance type does not exist',
                'i18n_code': 'instance_type_not_exist',
                'cid': get_current_cid()
            }, status_code = 400)

    possible_regions = get_provider_infos(provider, "regions")
    if region not in [region["name"] for region in possible_regions]:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'region does not exist',
            'i18n_code': 'region_not_exist',
            'cid': get_current_cid()
        }, status_code = 400)

    if exists_zone(zone, region, possible_regions):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'zone does not exist', 
            'i18n_code': 'zone_not_exist',
            'cid': get_current_cid()
        }, status_code = 400)

    if  len(get_dns_zones())>0 and userInstance.root_dns_zone in get_dns_zones():
        generate_dns = "true"

    from entities.Environment import Environment
    exist_env = Environment.getById(userInstance.environment_id, db)
    if not exist_env:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'environment not found',
            'i18n_code': 'environment_not_found',
            'cid': get_current_cid()
        }, status_code = 404)
    try:
        gitlab_project = get_gitlab_project(project_id, exist_project.gitlab_host, exist_project.access_token)
        reregister_instance(userInstance.id, provider, region, zone, instance_type, userInstance.root_dns_zone, exist_project.id, db)
        ami_image = get_os_image(region, zone)
        user_project_json = json.loads(json.dumps(exist_project, cls = AlchemyEncoder))
        env_json = json.loads(json.dumps(exist_env, cls = AlchemyEncoder))

        bt.add_task(create_instance,
            provider,
            ami_image,
            userInstance.id,
            current_user.email,
            instance_name,
            hashed_instance_name,
            env_json,
            region,
            zone,
            generate_dns,
            gitlab_project,
            user_project_json,
            instance_type,
            debug,
            centralized,
            userInstance.root_dns_zone,
            None,
            db
        )

        dumpedInstance = json.loads(json.dumps(userInstance, cls = AlchemyEncoder))
        new_instance_json = {
            **dumpedInstance,
            "environment": userInstance.environment.name,
            "path": userInstance.environment.path,
            "gitlab_project": userInstance.project.url
        }
        return JSONResponse(content = new_instance_json, status_code = 200)
    except auto.StackAlreadyExistsError:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'stack already exists',
            'i18n_code': 'stack_exists',
            'cid': get_current_cid()
        }, status_code = 409)
    except HTTPError as e:
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg,
            'i18n_code': e.headers["i18n_code"],
            'cid': get_current_cid()
        }, status_code = e.code)
    except Exception as exn:
        return JSONResponse(content = {
            'status': 'ko',
            'error': "{}".format(exn),
            'cid': get_current_cid()
        }, status_code = 500)

def provision_instance(current_user, payload, provider, region, zone, environment, db, bt: BackgroundTasks):
    instance_name = payload.name
    if is_not_subdomain_valid(instance_name):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'The instance name is not valid',
            'i18n_code': 'instance_name_invalid',
            'cid': get_current_cid()
        }, status_code = 400)

    project_id = payload.project_id
    project_name = payload.project_name
    project_url = payload.project_url
    debug = payload.debug
    instance_type = payload.type
    root_dns_zone = payload.root_dns_zone
    email = current_user.email
    hash, hashed_instance_name = generate_hashed_name(instance_name)
    log_msg("DEBUG", "[instance][provision_instance] hash = {}, hashed_instance_name = {}".format(hash, hashed_instance_name))

    generate_dns = "false"
    #? Cloud init will mv _gitlab-ci.yml ./.gitlab-ci.yml And create all the roles and playbook
    centralized = "none"
    exist_project = None

    if not exist_provider(provider):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'provider does not exist',
            'i18n_code': 'provider_not_exist',
            'cid': get_current_cid()
        }, status_code = 404)
    if  len(get_dns_zones())>0:
        generate_dns = "true"
        if is_empty(root_dns_zone):
            root_dns_zone = get_dns_zones()[0]
            log_msg("INFO", "[api_instance] root_dns_zone is empty, taking the default one {}".format(root_dns_zone))
        elif root_dns_zone not in get_dns_zones():
            log_msg("ERROR", "[api_instance] the root dns zone is not valid :{}".format(root_dns_zone))
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'please provide a valid root dns zone',
                'i18n_code': 'provide_valid_root_dns_zone',
                'cid': get_current_cid()
            }, status_code = 400)

    if is_empty(project_id) and is_empty(project_name) and is_empty(project_url):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'please provide a project id or a project name or a project url',
            'i18n_code':  'provide_project_id_or_name_or_url',
            'cid': get_current_cid()
        }, status_code = 400)

    if is_empty(instance_name):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'please provide instance name',
            'i18n_code':  'provide_instance_name',
            'cid': get_current_cid()
        }, status_code = 400)

    if is_not_empty(project_id):
        exist_project = get_user_project_by_id(project_id, current_user.id, db)
        if not exist_project:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found',
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

    if is_not_empty(project_name):
        exist_project = get_user_project_by_name(project_name, current_user.id, db)
        if is_empty(exist_project):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found',
                'i18n_code': 'project_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

    if is_not_empty(project_url):
        exist_project = get_user_project_by_url(project_url, current_user.id, db)
        if is_empty(exist_project):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found',
                'i18n_code': 'project_not_found_with_gitlab',
                'cid': get_current_cid()
            }, status_code = 404)

    possible_regions = get_provider_infos(provider, "regions")
    if region not in [region["name"] for region in possible_regions]:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'region does not exist',
            'i18n_code': 'region_not_exist',
            'cid': get_current_cid()
        }, status_code = 400)

    if exists_zone(zone, region, possible_regions):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'zone does not exist',
            'i18n_code': 'zone_not_exist',
            'cid': get_current_cid()
        }, status_code = 400)

    if is_empty(instance_type):
        instance_type = get_provider_available_instances_by_region_zone(provider, region, zone)[0]
    else:
        possible_types = get_provider_available_instances_by_region_zone(provider, region, zone)
        if instance_type not in possible_types:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Instance type does not exist',
                'i18n_code': 'instance_type_not_exist',
                'cid': get_current_cid()
            }, status_code = 400)
    from entities.Environment import Environment
    exist_env = Environment.getByPath(environment, db)

    try:
        if not exist_env:
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'environment not found',
                'i18n_code': 'environment_not_found',
                'cid': get_current_cid()
            }, status_code = 404)

        gitlab_project = get_project_quietly(exist_project)
        if is_http_error_fetching_project(gitlab_project):
            return JSONResponse(content= {
                'status': 'ko',
                'error': gitlab_project['reason'],
                'i18n_code': gitlab_project['i18n_code'],
                'cid': get_current_cid()
            }, status_code = gitlab_project['http_code'])
        elif is_not_project_found_in_gitlab(gitlab_project):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'project not found with gitlab',
                'i18n_code':  'project_not_found_with_gitlab',
                'cid': get_current_cid()
            }, status_code = 404)

        exist_project = refresh_project_credentials(db, exist_project, gitlab_project)
        project_playbooks = get_gitlab_project_playbooks(exist_project.id, exist_project.gitlab_host, exist_project.access_token)
        check_instance_name_validity(instance_name)
        check_exist_instance(current_user.id, instance_name, db)
        if len(project_playbooks)>0:
            #? Cloud init will contatenante _gitlab-ci.yml in the existing one And create all the missing roles and playbook
            centralized = "true"
            if instance_name in [name.split("playbook-")[1] for name in project_playbooks]:
                return JSONResponse(content = {
                    'status': 'ko',
                    'error': 'playbook already exists',
                    'i18n_code':  'playbook_exists',
                    'cid': get_current_cid()
                }, status_code = 404)

        new_instance = register_instance(hash, provider, region, zone, current_user.id, instance_name.lower(), instance_type, environment, gitlab_project, root_dns_zone, db)
        ami_image = get_os_image(region, zone)
        user_project_json = json.loads(json.dumps(exist_project, cls = AlchemyEncoder))
        env_json = json.loads(json.dumps(exist_env, cls = AlchemyEncoder))

        bt.add_task(create_instance,
            provider,
            ami_image,
            new_instance.id,
            email,
            instance_name,
            hashed_instance_name,
            env_json,
            region,
            zone,
            generate_dns,
            gitlab_project,
            user_project_json,
            instance_type,
            debug,
            centralized,
            root_dns_zone,
            payload.args,
            db
        )

        dumpedInstance = json.loads(json.dumps(new_instance, cls = AlchemyEncoder))
        new_instance_json = {**dumpedInstance, "environment": new_instance.environment.name, "path": new_instance.environment.path, "gitlab_project": new_instance.project.url}
        return JSONResponse(content = new_instance_json, status_code = 200)
    except auto.StackAlreadyExistsError as sae:
        log_msg("ERROR", "[instance][provision_instance] unexpected StackAlreadyExistsError:{}".format(sae))
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'stack already exists',
            'i18n_code': 'stack_exists',
            'cid': get_current_cid()
        }, status_code = 409)
    except HTTPError as e:
        log_msg("ERROR", "[instance][provision_instance] unexpected HTTPError:{}".format(e))
        return JSONResponse(content = {
            'status': 'ko',
            'error': e.msg,
            'i18n_code': e.headers['i18n_code'],
            'cid': get_current_cid()
        }, status_code = e.code)
    except Exception as exn:
        log_msg("ERROR", "[instance][provision_instance] unexpected error: type = {}, msg = {}, line = {}".format(type(exn).__name__, exn, exn.__traceback__.tb_lineno))
        return JSONResponse(content = {
            'status': 'ko',
            'error': "{}".format(exn),
            'cid': get_current_cid()
        }, status_code = 500)

def get_instances(current_user, provider, region, db):
    if not exist_provider(provider):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'provider does not exist',
            'i18n_code': 'provider_not_exist',
            'cid': get_current_cid()
        }, status_code = 404)

    from entities.Instance import Instance
    from entities.Access import Access
    userRegionInstances = Instance.getActiveUserInstancesPerRegion(current_user.id, provider, region, db)
    other_instances_access = Access.getUserAccessesByType(current_user.id, "instance", db)
    other_instances_ids = [access.object_id for access in other_instances_access]
    other_instances = Instance.findInstancesByRegion(other_instances_ids, provider, region, db)
    userRegionInstances.extend(other_instances)
    instances = []
    for instance in userRegionInstances:
        dumpedInstance = json.loads(json.dumps(instance, cls = AlchemyEncoder))
        instances.append({**dumpedInstance, "environment": instance.environment.name, "path": instance.environment.path})
    return JSONResponse(content = instances, status_code = 200)
