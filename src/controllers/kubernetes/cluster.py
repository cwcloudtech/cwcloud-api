from fastapi.responses import JSONResponse

from entities.kubernetes.Cluster import Cluster
from utils.kubernetes.k8s_management import get_dumped_json

def get_clusters_limited(current_user, db):
    clusters = Cluster.getAllForUser(db) 
    cluster_dicts = [{"id": cluster.id, "name": cluster.name} for cluster in clusters]
    return JSONResponse(content = get_dumped_json(cluster_dicts), status_code = 200)
