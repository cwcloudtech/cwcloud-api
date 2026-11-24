import os
import json
import googleapiclient.discovery

from google.oauth2 import service_account
from google.cloud import storage, artifactregistry, artifactregistry_v1beta2, compute_v1, dns
from google.iam.v1 import iam_policy_pb2
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

from utils.common import is_enabled, unbase64
from utils.logger import log_msg

_gcp_project_id = os.getenv('GCP_PROJECT_ID')
_google_app_cred_str = unbase64(os.getenv('GCP_APPLICATION_CREDENTIALS'))
_google_app_credentials = json.loads(_google_app_cred_str) if is_enabled(_google_app_cred_str) else _google_app_cred_str

def generate_access_token(service_account_email):
    credentials = service_account.Credentials.from_service_account_info(_google_app_credentials)
    service = googleapiclient.discovery.build("iam", "v1", credentials = credentials)
    key = (
        service.projects()
        .serviceAccounts()
        .keys()
        .create(name = "projects/-/serviceAccounts/" + service_account_email, body = {})
        .execute()
    )

    json_key = json.loads(unbase64(key['privateKeyData']))
    log_msg("DEBUG", "[gcp][generate_access_token] json_key = {}".format(json_key))

    new_credentials = service_account.Credentials.from_service_account_info(json_key, scopes = ['https://www.googleapis.com/auth/cloud-platform'])
    request = Request()
    try:
        new_credentials.refresh(request)
    except RefreshError as e:
        log_msg("WARN", "[gcp][generate_access_token] could not refresh the token: e = {}, new_credentials = {}".format(e, new_credentials))

    access_token = new_credentials.token
    return access_token

def get_gcp_instance_name(zone, name_instance):
    credentials = service_account.Credentials.from_service_account_info(_google_app_credentials, scopes = ['https://www.googleapis.com/auth/cloud-platform'])
    client = compute_v1.InstancesClient(credentials = credentials)
    instance_filter = f'name = {name_instance}*'
    request = compute_v1.ListInstancesRequest(project = _gcp_project_id, zone = zone, filter = instance_filter)
    response = client.list(request = request)
    instance_name = name_instance
    for instance in response:
        instance_name = instance.name
    return instance_name

def get_artifact_registry_repository(region, hashed_name):
    credentials = service_account.Credentials.from_service_account_info(_google_app_credentials)
    client = artifactregistry.ArtifactRegistryClient(credentials = credentials)
    parent = f"projects/{_gcp_project_id}/locations/{region}"
    repositories = client.list_repositories(parent = parent)
    for repository in repositories:
        if repository.name.endswith(hashed_name):
            return(repository)

def update_credentials_policy_registry(hashed_name, region, type):
    credentials = service_account.Credentials.from_service_account_info(_google_app_credentials)
    service = googleapiclient.discovery.build("iam", "v1", credentials = credentials)
    name = hashed_name + "-sa"

    my_service_account = (
        service.projects()
        .serviceAccounts()
        .create(
            name = "projects/" + _gcp_project_id,
            body = {"accountId": name, "serviceAccount": {"displayName": name}},
        )
        .execute()
    )

    repository = get_artifact_registry_repository(region, hashed_name)

    client = artifactregistry_v1beta2.ArtifactRegistryClient(credentials = credentials)
    resource_name = "projects/" + _gcp_project_id + "/locations/" + region + "/repositories/" + hashed_name

    if type == "public":
        iam_policy = {
            "bindings": [
                {
                    "role": "roles/artifactregistry.reader",
                    "members": ["allUsers"],
                },
                {
                    "role": "roles/artifactregistry.admin",
                    "members": [f"serviceAccount:{my_service_account['email']}"],
                }
            ]
        }
    else:
        iam_policy = {
            "bindings": [
                {
                    "role": "roles/artifactregistry.admin",
                    "members": [f"serviceAccount:{my_service_account['email']}"],
                }
            ]
        }

    request = iam_policy_pb2.SetIamPolicyRequest(
        resource = resource_name,
        policy = iam_policy,
    )

    if repository:
        client.set_iam_policy(request = request)

    log_msg("DEBUG", "[update_credentials_policy_registry] generate access token for: {}".format(my_service_account["email"]))
    access_token = generate_access_token(my_service_account["email"])
    return access_token

def delete_registry_service_account(email):
    credentials = service_account.Credentials.from_service_account_info(_google_app_credentials)
    service = googleapiclient.discovery.build("iam", "v1", credentials = credentials)
    service.projects().serviceAccounts().delete(name = f"projects/{_gcp_project_id}/serviceAccounts/{email}").execute()

def get_gcp_bucket(hashed_bucket_name):
    credentials = service_account.Credentials.from_service_account_info(_google_app_credentials)
    client = storage.Client(project = _gcp_project_id, credentials = credentials)
    buckets = client.list_buckets()
    if not buckets:
        return None

    for bucket in buckets:
        if bucket.name.startswith(hashed_bucket_name):
           return bucket

    return None

def update_policy_and_credentials_bucket(hashed_bucket_name, bucket_type):
    credentials = service_account.Credentials.from_service_account_info(_google_app_credentials)
    service = googleapiclient.discovery.build("iam", "v1", credentials = credentials)
    name = hashed_bucket_name + "-sa"
    my_service_account = (
        service.projects()
        .serviceAccounts()
        .create(
            name = "projects/" + _gcp_project_id,
            body = {"accountId": name, "serviceAccount": {"displayName": name}},
        )
        .execute()
    )

    bucket = get_gcp_bucket(hashed_bucket_name)
    if bucket is None:
        error_msg = "Bucket not found : project_id = {}, hashed_bucket_name = {}".format(_gcp_project_id, hashed_bucket_name)
        log_msg("ERROR", error_msg)
        raise RuntimeError(error_msg)

    if bucket_type == "public-read":
        iam_configuration = bucket.iam_configuration
        iam_configuration.public_access_prevention = "inherited"
        iam_configuration.uniform_bucket_level_access = False
        iam_configuration.bucket_policy_only = False
        bucket.update()
        policy = bucket.get_iam_policy(requested_policy_version = 3)
        policy.bindings.append({
            "role": "roles/storage.admin",
            "members": [f"serviceAccount:{my_service_account['email']}"],
        })
        bucket.set_iam_policy(policy)
        bucket.make_public()
        for blob in bucket.list_blobs():
          blob.make_public()

    else:
        iam_configuration = bucket.iam_configuration
        iam_configuration.public_access_prevention = "enforced"
        iam_configuration.uniform_bucket_level_access = False
        iam_configuration.bucket_policy_only = True

        bucket.update()
        policy = bucket.get_iam_policy(requested_policy_version = 3)

        policy.bindings.append({
            "role": "roles/storage.admin",
            "members": [f"serviceAccount:{my_service_account['email']}"],
        })

        bucket.set_iam_policy(policy)
    storage_client = storage.Client(project = _gcp_project_id, credentials = credentials)
    hmac_key, secret = storage_client.create_hmac_key(
        service_account_email = my_service_account["email"], project_id = _gcp_project_id
    )

    return (hmac_key.access_id, secret, my_service_account['uniqueId'])

def delete_bucket_service_account(email):
    credentials = service_account.Credentials.from_service_account_info(_google_app_credentials)
    service = googleapiclient.discovery.build("iam", "v1", credentials = credentials)
    service.projects().serviceAccounts().delete(name = f"projects/{_gcp_project_id}/serviceAccounts/{email}").execute()

def update_registry_token(hashed_name):
    service_account_email = f"{hashed_name}-sa@{_gcp_project_id}.iam.gserviceaccount.com"
    return generate_access_token(service_account_email)

def update_bucket_keys(hashed_bucket_name):
    credentials = service_account.Credentials.from_service_account_info(_google_app_credentials)
    storage_client = storage.Client(project = _gcp_project_id, credentials = credentials)
    service_account_email = f"{hashed_bucket_name}-sa@{_gcp_project_id}.iam.gserviceaccount.com"
    hmac_keys = storage_client.list_hmac_keys(project_id = _gcp_project_id)
    for hmac_key in hmac_keys:
        if hmac_key.service_account_email == service_account_email:
            access_id = hmac_key.access_id

    delete_old_bucket_keys(access_id)
    hmac_key, secret = storage_client.create_hmac_key(
        service_account_email = service_account_email, project_id = _gcp_project_id
    )
    return (hmac_key.access_id, secret)

def delete_old_bucket_keys(access_id):
    credentials = service_account.Credentials.from_service_account_info(_google_app_credentials)
    storage_client = storage.Client(project = _gcp_project_id, credentials = credentials)
    hmac_key = storage_client.get_hmac_key_metadata(
        access_id, project_id = _gcp_project_id
    )
    hmac_key.state = "INACTIVE"
    hmac_key.update()
    hmac_key.delete()

def get_provider_dns_zone_domain_name(dns_zone_name):
    credentials = service_account.Credentials.from_service_account_info(
            _google_app_credentials,
            scopes = ['https://www.googleapis.com/auth/cloud-platform'])  

    client = dns.Client(project=_gcp_project_id, credentials=credentials)
    dns_zone = client.zone(name=dns_zone_name)
    dns_zone.reload()
    return dns_zone.dns_name
