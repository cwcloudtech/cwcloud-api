import os

import ovh

from utils.logger import log_msg
from utils.provider import get_provider_dns_zones

service_name = os.getenv('OVH_SERVICENAME')
ovh_client = ovh.Client(
    endpoint = os.getenv('OVH_ENDPOINT'),
    application_key = os.getenv('OVH_APPLICATION_KEY'),
    application_secret = os.getenv('OVH_APPLICATION_SECRET'),
    consumer_key = os.getenv('OVH_CONSUMER_KEY'),
)

def find_registry_id_by_name(name):
    registries = ovh_client.get('/cloud/project/{}/containerRegistry'.format(service_name))
    target_registry_id = next(reg["id"] for reg in registries if reg['name'] == name)
    return target_registry_id

def update_ovh_registry_credentials(name):
    registry_id = find_registry_id_by_name(name)
    users = ovh_client.get('/cloud/project/{}/containerRegistry/{}/users'.format(service_name, registry_id))
    users_ids = [user["id"] for user in users]
    for user_id in users_ids:
        ovh_client.delete('/cloud/project/{}/containerRegistry/{}/users/{}'.format(service_name, registry_id, user_id))
    created_user = ovh_client.post('/cloud/project/{}/containerRegistry/{}/users'.format(service_name, registry_id), email = f'{name}@gmail.com', login = "cloud")
    return {"login": created_user["user"], "password": created_user["password"]}

def update_ovh_bucket_credentials(user_id):
    credentials = ovh_client.get('/cloud/project/{}/user/{}/s3Credentials'.format(service_name, user_id))
    access_keys = [credential["access"] for credential in credentials]
    for access_key in access_keys:
        ovh_client.delete('/cloud/project/{}/user/{}/s3Credentials/{}'.format(service_name, user_id, access_key))
    created_credentials = ovh_client.post('/cloud/project/{}/user/{}/s3Credentials'.format(service_name, user_id))
    return {"access_key": created_credentials["access"], "secret_key": created_credentials["secret"]}

def create_ovh_bucket(name, region, bucket_user_id):
    user_id = int(bucket_user_id)
    bucket = ovh_client.post('/cloud/project/{}/region/{}/storage'.format(service_name, region), name = name, ownerId = user_id)
    credentials = ovh_client.get('/cloud/project/{}/user/{}/s3Credentials'.format(service_name, user_id))
    log_msg("DEBUG", "[create_ovh_bucket] bucket credentials = {}".format(credentials))
    access_keys = [credential["access"] for credential in credentials]
    for access_key in access_keys:
        ovh_client.delete('/cloud/project/{}/user/{}/s3Credentials/{}'.format(service_name, user_id, access_key))
    created_credentials = ovh_client.post('/cloud/project/{}/user/{}/s3Credentials'.format(service_name, user_id))
    endpoint = bucket["virtualHost"]
    return (endpoint, created_credentials["access"], created_credentials["secret"])

def delete_ovh_bucket(name, region, user_id):
    ovh_client.delete('/cloud/project/{}/region/{}/storage/{}'.format(service_name, region, name))
    credentials = ovh_client.get('/cloud/project/{}/user/{}/s3Credentials'.format(service_name, user_id))
    access_keys = [credential["access"] for credential in credentials]
    for access_key in access_keys:
        ovh_client.delete('/cloud/project/{}/user/{}/s3Credentials/{}'.format(service_name, user_id, access_key))
    ovh_client.delete('/cloud/project/{}/user/{}'.format(service_name, user_id))
def list_ovh_dns_records():
    zones =  get_provider_dns_zones("ovh")
    records = []
    for zone in zones:
        record_ids = ovh_client.get(f'/domain/zone/{zone}/record')
        for record_id in record_ids:
            record = ovh_client.get(f'/domain/zone/{zone}/record/{record_id}')
            records.append({
                'id': record_id,
                'zone': zone,
                'record': record['subDomain'],
                'type': record['fieldType'],
                'ttl': record['ttl'],
                'data': record['target']
            })
    return records

def create_custom_dns_record(record_name, dns_zone, record_type, ttl, data):
    record = ovh_client.post(f'/domain/zone/{dns_zone}/record', fieldType = record_type, subDomain = record_name, ttl = ttl, target = data)
    return record

def delete_ovh_dns_record(record_id, dns_zone):
    ovh_client.delete(f'/domain/zone/{dns_zone}/record/{record_id}')
