import os
import yaml

import pulumi_ovh as ovh
import pulumiverse_scaleway as scaleway
import pulumi_aws as aws
import pulumi_cloudflare as cloudflare

from utils.common import is_empty, is_not_empty, is_not_empty_key
from utils.logger import log_msg

def register_cloudflare_domain(value, environment, instance_ip, root_dns_zone):
    dns_zone = "{}.{}".format(environment, root_dns_zone)
    record_name = "{}.{}".format(value, environment)
    log_msg("INFO", "[register_domain][cloudflare] register domain {}.{}".format(record_name, dns_zone))
    zone_id = get_zone_id(root_dns_zone)
    if is_empty(zone_id):
        log_msg("ERROR", "[dns_zones][register_cloudflare_domain] No zone id found for root_dns_zone = {}".format(root_dns_zone))
        return

    cloudflare.Record(record_name,
        zone_id = zone_id,
        name = record_name,
        value = instance_ip,
        type = "A",
        ttl = 3600)

def register_scaleway_domain(record_name, environment, instance_ip, root_dns_zone):
    dns_zone = "{}.{}".format(environment, root_dns_zone)
    log_msg("INFO", "[register_domain][scaleway] register domain {}.{}".format(record_name, dns_zone))
    scaleway.DomainRecord(record_name,
        name = record_name,
        data = instance_ip,
        dns_zone = dns_zone,
        ttl = 3600,
        type = "A")

def register_ovh_domain(record_name, environment, instance_ip, root_dns_zone):
    dns_zone = "{}.{}".format(environment, root_dns_zone)
    sub_domain = "{}.{}".format(record_name, environment)
    log_msg("INFO", "[register_domain][ovh] register domain {}.{}".format(record_name, dns_zone))
    ovh.domain.ZoneRecord(sub_domain,
        fieldtype = "A",
        subdomain = sub_domain,
        target = instance_ip,
        ttl = 3600,
        zone = root_dns_zone)

def register_aws_domain(record_name, environment, instance_ip, root_dns_zone):
    dns_zone = "{}.{}".format(environment, root_dns_zone)
    sub_domain = "{}.{}".format(record_name, environment)
    log_msg("INFO", "[register_domain][aws] register domain {}.{}".format(record_name, dns_zone))

    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'cloud_environments.yml'))
    with open(config_path, "r") as stream:
        loaded_data = yaml.safe_load(stream)
        hosted_zone_id = loaded_data['dns_hosted_zone_id']

    aws.route53.Record(resource_name = sub_domain,
        zone_id = hosted_zone_id,
        name = sub_domain,
        type = "A",
        ttl = 300,
        records = [instance_ip])

def get_dns_zone_driver(dns_zone):
    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'cloud_environments.yml'))
    dns_zones = []
    with open(config_path, "r") as stream:
        loaded_data = yaml.safe_load(stream)
        dns_zones = loaded_data.get('dns_zones', [])

    filtered_dns_zones = [zone for zone in dns_zones if zone['name'] == dns_zone]
    if len(filtered_dns_zones) >0:
        strategy = filtered_dns_zones[0]['driver'] if 'driver' in filtered_dns_zones[0] and is_not_empty(filtered_dns_zones[0]['driver']) else filtered_dns_zones[0]['strategy']
        return strategy.replace("Strategy", "Driver")
    return False

def get_dns_zones():
    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'cloud_environments.yml'))
    result = []
    with open(config_path, "r") as stream:
        loaded_data = yaml.safe_load(stream)
        if 'dns_zones' in loaded_data:
            result = [dns_zone['name'] for dns_zone in loaded_data['dns_zones']]
        else:
            result = []
    return result

def get_zone_id(dns_zone):
    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'cloud_environments.yml'))
    with open(config_path, "r") as stream:
        loaded_data = yaml.safe_load(stream)
        if 'dns_zones' in loaded_data:
            for z in loaded_data['dns_zones']:
                if z['name'] == dns_zone and is_not_empty_key(z, 'zone_id'):
                    return z['zone_id']

    return None

def get_first_dns_zone_doc():
    zones = get_dns_zones()
    if len(zones) >= 1:
        return zones[0]

    return "comwork.cloud"
