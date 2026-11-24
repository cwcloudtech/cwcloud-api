import json

import yaml
from fastapi.responses import JSONResponse
from kubernetes import client, config
from urllib3.exceptions import MaxRetryError

from entities.Environment import Environment
from entities.kubernetes.Cluster import Cluster
from entities.kubernetes.Deployment import Deployment
from entities.Project import Project
from schemas.Kubernetes import DeploymentSchema
from schemas.User import UserSchema
from utils.bytes_generator import generate_random_bytes
from utils.common import is_not_empty, is_true
from utils.encoder import AlchemyEncoder
from utils.kubernetes.deployment_env import push_charts
from utils.kubernetes.k8s_management import (delete_custom_resource,
                                             set_git_config)
from utils.list import unmarshall_list_array
from utils.logger import log_msg
from utils.observability.cid import get_current_cid

GROUP = "helm.toolkit.fluxcd.io"
VERSION = "v2beta2"
PLURAL = "helmreleases"
NAMESPACE = "flux-system"

def get_deployments(current_user: UserSchema, db):
    if current_user.is_admin:
        deployments = Deployment.getAll(db)
    else:
        deployments = Deployment.getAllByUser(current_user.id, db)

    deploymentJson = json.loads(json.dumps(deployments, cls = AlchemyEncoder))
    
    deploymentJson = [
        {
            **deployment,
            "namespace": f'{deployment["name"]}-{deployment["hash"]}'
        } for deployment in deploymentJson
    ]
    
    return JSONResponse(content = deploymentJson, status_code = 200)

def create_new_deployment(current_user:UserSchema, deployment:DeploymentSchema, db):
    env: Environment = Environment.getById(deployment.env_id, db)

    if not env and env.type != "vm":
        return JSONResponse(content = {
            'status': 'ko',
            'message': 'environment not found',
            'i18n_code': 'environment_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    project = Project.getById(deployment.project_id, db)
    
    if not project:
        return JSONResponse(content = {
            'status': 'ko',
            'message': 'project not found',
            'i18n_code': 'project_not_found',
            'cid': get_current_cid()
        }, status_code = 404)
    
    deployments = Deployment.getAllByProject(project.id, db)
    if is_not_empty(deployments) > 0 and deployments[0].env_id != deployment.env_id:
        return JSONResponse(content = {
            'status': 'ko',
            'message': "can't select a different environment for this project",
            'i18n_code': 'can_not_selecte_environment_for_project',
            'cid': get_current_cid()
        }, status_code = 400)
    
    cluster = Cluster.getById(deployment.cluster_id, db)
    if not cluster:
        return JSONResponse(content = {
            'status': 'ko',
            'message': 'cluster not found',
            'i18n_code': 'region_not_exist',
            'cid': get_current_cid()
        }, status_code = 404)
        
    charts = unmarshall_list_array(env.roles)
    external_charts = unmarshall_list_array(env.external_roles)

    generatedHash = generate_random_bytes(6)
    deployment.name = deployment.name.lower()
    kubeconfigFile = cluster.getKuberConfigFileByClusterId(cluster.id, db)
    generatedName = f'{deployment.name}-{generatedHash}'
    push_charts(
        project.id,
        project.gitlab_host,
        deployment.name,
        generatedName,
        env.name,
        env.environment_template,
        env.doc_template,
        project.access_token,
        charts,
        external_charts,
        deployment.args
    )
    set_git_config(kubeconfigFile.content,generatedName,generatedName,project)
    deployment = Deployment(name=deployment.name,
                            description=deployment.description,
                            cluster_id = deployment.cluster_id,
                            project_id = deployment.project_id,
                            env_id = deployment.env_id,
                            hash=generatedHash,
                            user_id=current_user.id)
    deployment.save(db)
    deploymentJson = json.loads(json.dumps(deployment, cls = AlchemyEncoder))

    return JSONResponse(content = deploymentJson, status_code = 201)

def get_deployment(current_user:UserSchema,deployment_id:int, db):
    deployment = Deployment.findOne(deployment_id, db)
    if not deployment:
        return JSONResponse(content = {
            'status': 'ko',
            'message': "deployment not found",
            'i18n_code': 'deployment_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    if deployment.user_id != current_user.id and not current_user.is_admin:
        return JSONResponse(content = {
            'status': 'ko',
            'message': "you don't have permission to get this deployment",
            'i18n_code': 'no_premission_for_deployment',
            'cid': get_current_cid()
        }, status_code = 403)
    
    kubeConfig = Cluster.getKuberConfigFileByClusterId(deployment.cluster_id, db)
    config_file = yaml.safe_load(kubeConfig.content)
    config.load_kube_config_from_dict(config_file)
    v1 = client.CoreV1Api()
    
    try:
        pods = v1.list_namespaced_pod(f'{deployment.name}-{deployment.hash}').items
    except MaxRetryError:
        return JSONResponse(content = {
            'status': 'ko',
            'message': "couldn't connect to the cluster",
            'i18n_code': 'can_not_connect_to_cluster',
            'cid': get_current_cid()
        }, status_code = 500)
    
    project = Project.getById(deployment.project_id, db)
    env = Environment.getById(deployment.env_id, db)
    
    containers = []
    podsData = [] 
    for pod in pods:
        podsData.append({
            "id": pod.metadata.name + deployment.name,
            "name": pod.metadata.name,
            "status": pod.status.phase,
            "ip": pod.status.pod_ip,
            "start_time": pod.status.start_time.strftime('%Y-%m-%dT%H:%M:%S.%f'),
        })
    
        for container in zip(pod.spec.containers,pod.status.container_statuses):
            if container[1].state.waiting:
                podsData[-1]["status"] = container[1].state.waiting.reason
            containers.append({
                "id": container[0].name + pod.metadata.name,
                "name": container[0].name,
                "image": container[0].image,
                "started": container[1].started,
                "restart_count": container[1].restart_count,
                "state": {
                    "running": bool(container[1].state.running),
                    "terminated": bool(container[1].state.terminated),
                    "waiting": bool(container[1].state.waiting),
                },
            })

    return JSONResponse(content = {
            "name": deployment.name,
            "namespace": f'{deployment.name}-{deployment.hash}',
            "pods": podsData,
            "containers": containers ,
            "project": {
                "id": deployment.project_id,
                "name": project.name,
            },
            "environment": {
                "id": deployment.env_id,
                "name": env.name,
            }
        }, status_code = 200)

def delete_deployment(current_user:UserSchema,deployment_id:int, db):
    deployment = Deployment.findOne(deployment_id, db)
    if not deployment:
        return JSONResponse(content = {
            'status': 'ko',
            'message': 'deployment not found',
            'i18n_code': 'deployment_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    if deployment.user_id != current_user.id and not current_user.is_admin:
        return JSONResponse(content = {
            'status': 'ko',
            'message': "you don't have permission to delete this deployment",
            'i18n_code': 'no_premission_for_deployment',
            'cid': get_current_cid()
        }, status_code = 403)
    
    cluster = Cluster.getById(deployment.cluster_id, db)
    kubeconfigFile = cluster.getKuberConfigFileByClusterId(cluster.id, db)
    deleted = delete_custom_resource(
        GROUP,
        VERSION,
        PLURAL,
        f'{deployment.name}-{deployment.hash}-release',
        NAMESPACE,
        kubeconfigFile.content
    )

    deployment.delete(db)
    if is_true(deleted):
        try:
            config.load_kube_config_from_dict(yaml.safe_load(kubeconfigFile.content))
            v1 = client.CoreV1Api()
            v1.delete_namespace(f'{deployment.name}-{deployment.hash}')
        except Exception as e:
            log_msg("ERROR", f"[Kubernetes][delete_deployment] Error deleting namespace: {str(e)}")
        return JSONResponse(content = {
            'status': 'ok',
            'message': 'deployment deleted'
        }, status_code = 200)
    else:
        return JSONResponse(content = {
            'status': 'ko',
            'message': "couldn't delete deployment from the cluster, but it was deleted from the database",
            'i18n_code': 'can_not_delete_deployment_from_cluster',
            'cid': get_current_cid()
        }, status_code = 200)
