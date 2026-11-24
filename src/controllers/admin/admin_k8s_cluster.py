from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
from kubernetes import client, config

from schemas.User import UserSchema
from entities.kubernetes.Cluster import Cluster
from entities.kubernetes.KubeconfigFile import KubeConfigFile

from utils.logger import log_msg
from utils.yaml import read_uploaded_yaml_file
from utils.kubernetes.k8s_management import get_dumped_json, install_flux
from utils.observability.cid import get_current_cid

def get_all_clusters(db):
    clusters = Cluster.getAll(db) 
    response = get_dumped_json(clusters)
    return JSONResponse(content = response, status_code = 200)

def get_cluster(cluster_id, db) -> Cluster:
    cluster = Cluster.getById(cluster_id, db)
    if not cluster:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'cluster not found',
            'i18n_code': 'cluster_not_found',
            'cid': get_current_cid()
        }, status_code = 404)
    return cluster

def get_clusters_byKubeconfigFile(current_user, kubeconfig_file_id, db):
    clusters = Cluster.findByKubeConfigFile(kubeconfig_file_id, db)
    if not clusters:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'clusters not found', 
            'i18n_code': 'clusters_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    dumpedClusters = get_dumped_json(clusters)
    return JSONResponse(content = dumpedClusters, status_code = 200)

def get_cluster_infos(current_user, cluster_id, db):
    try:
        cluster = get_cluster(cluster_id, db)
        kubeconfigFile = KubeConfigFile.findOne(cluster.kubeconfig_file_id, db)
        if not kubeconfigFile:
            return JSONResponse(content={
                    'status': 'ko',
                    'error': 'kubeconfig file not found',
                    'i18n_code': 'kubeconfig_not_found',
                    'cid': get_current_cid()
                }, status_code=404
            )

        kc_content = read_uploaded_yaml_file(kubeconfigFile.content)
        config.load_kube_config_from_dict(kc_content)
        core_v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        v1Server = client.VersionApi()
        custom_obj = client.CustomObjectsApi()

    # Get the server info
        server_version = v1Server.get_code()
        pods = core_v1.list_pod_for_all_namespaces(watch=False)
        nodes = core_v1.list_node()
        node_metrics = custom_obj.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")

    # Get the max pods capacity of the cluster
        max_pods = 0
        nodes_result = []
        for i in range(len(nodes.items)):
            try:
                node = nodes.items[i]
                node_metric = node_metrics['items'][i]['usage']
                
                max_pods += int(node.status.allocatable.get("pods", 0))
                nodes_result.append({
                    "name": node.metadata.name,
                    "ip": node.status.addresses[0].address if node.status.addresses else "N/A",
                    "status": node.status.conditions[3].type if len(node.status.conditions) > 3 else "Unknown",
                    "t_cpu": node.status.capacity.get("cpu", "N/A"),
                    "t_memory": node.status.capacity.get("memory", "N/A"),
                    "u_cpu": node_metric.get('cpu', "N/A"),
                    "u_memory": node_metric.get('memory', "N/A")
                })
            except (IndexError, KeyError) as e:
                log_msg("ERROR", f"[get_cluster_infos] Error processing node {i}: {str(e)}", True)
                continue

        pods_result = [
            {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "ip": pod.status.pod_ip or "N/A",
                "status": pod.status.phase or "Unknown"
            }
            for pod in pods.items
            if pod and pod.metadata and pod.status
        ]

        deployments_result = [
            {
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace,
                "replicas": getattr(deployment.status, 'replicas', 0),
                "available_replicas": getattr(deployment.status, 'available_replicas', 0),
                "ready_replicas": getattr(deployment.status, 'ready_replicas', 0),
                "updated_replicas": getattr(deployment.status, 'updated_replicas', 0),
                "age": deployment.metadata.creation_timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f')
            }
            for deployment in apps_v1.list_deployment_for_all_namespaces().items
            if deployment and deployment.metadata and deployment.status
        ]
        
        namespaces = core_v1.list_namespace().items

        return JSONResponse(
            content={
                "server_info": {
                    "version": server_version.git_version,
                    "platform": server_version.platform,
                },
                "pods": pods_result,
                "nodes": nodes_result,
                "max_pods": max_pods,
                "total_namespaces": len(namespaces),
                "deployments": deployments_result
            },
            status_code=status.HTTP_200_OK
        )

    except HTTPException as he:
        raise
    except Exception as e:
        log_msg("ERROR", f"[get_cluster_infos] Failed to get cluster information: {str(e)}", True)
        return JSONResponse(
            content={
                'status': 'ko',
                'error': f'Failed to get cluster information: {str(e)}',
                'i18n_code': 'cluster_info_failed',
                'cid': get_current_cid()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def save_kubeconfig(current_user:UserSchema, kubeconfig:UploadFile, db:Session):
    file = kubeconfig.file.read()
    
    kubeconfigFile = KubeConfigFile(content = file , owner_id = current_user.id)
    kubeconfigFile.save(db)
    
    try:
        read_clusters_and_save(file, kubeconfigFile.id, db)
    except Exception:
        kubeconfigFile.delete(db)
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'please verify the kubeconfig file', 
            'i18n_code': 'verify_kubeconfig_file',
            'cid': get_current_cid()
        }, status_code = 400)
    
    kubeconfig.file.close()
    return JSONResponse(content = {
            'status':'ok',
            'message': 'kubeconfig successfully uploaded',
            'file_id':kubeconfigFile.id
        }, status_code = 200)

def read_clusters_and_save(file, file_id, db):
    kc_content = read_uploaded_yaml_file(file)
    
    config.load_kube_config_from_dict(kc_content)
    v1Server = client.VersionApi()
    server_version = v1Server.get_code()
    
    for cluster in kc_content.get('clusters',[]):
        cl = Cluster()
        cl.name = cluster.get('name')
        cl.kubeconfig_file_id = file_id
        cl.platform = server_version.platform,
        cl.version = server_version.git_version,
        cl.save(db)
        install_flux(file)

def delete_cluster_by_id(current_user, cluster_id, db):
    cluster = get_cluster(cluster_id, db)
    if cluster is None:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'cluster not found', 
            'i18n_code': 'cluster_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    Cluster.deleteOne(cluster.id, db)
    return JSONResponse(content = {
        'status': 'ok',
        'message': 'Cluster successfully deleted'
    }, status_code = 200)
