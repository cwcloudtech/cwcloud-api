import os
import yaml

from urllib.error import HTTPError

from utils.common import is_empty
from utils.logger import log_msg

def exist_provider(providerName):
    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'cloud_environments.yml'))
    result = []
    with open(config_path, "r") as stream:
        loaded_data = yaml.safe_load(stream)
        result = loaded_data['providers']
        providers = [p for p in result if p['name'] == providerName]
    return len(providers)>0

def get_providers():
    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'cloud_environments.yml'))
    result = []
    with open(config_path, "r") as stream:
        loaded_data = yaml.safe_load(stream)
        result = loaded_data['providers']
    return result

def get_provider_infos(provider, key):
    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'cloud_environments.yml'))
    result = []
    with open(config_path, "r") as stream:
        loaded_data = yaml.safe_load(stream)
        result = loaded_data['providers']
        provider = [p for p in result if p['name'] == provider]
        if not len(provider)>0:
            raise HTTPError("provider_not_exist", 404, 'provider not found', hdrs = {"i18n_code": "provider_not_exist"}, fp = None)
    return provider[0][key]

def get_driver(provider):
    driver = get_provider_infos(provider, 'driver')
    if is_empty(driver):
        driver = get_provider_infos(provider, 'strategy')
    return driver.replace("Strategy", "Driver")

def get_provider_instance_price(provider, region, zone, type):
    instances_pricing = get_provider_instances_pricing_by_region_zone(provider, region, zone)
    filtered_instances_pricing = [instance for instance in instances_pricing if instance['name'] == type]
    if not len(filtered_instances_pricing)>0:
        raise HTTPError("instance_type_in_zone_not_found", 404, 'instance type in this zone not found', hdrs = {"i18n_code": "instance_type_in_zone_not_found"}, fp = None)
    instance_price = filtered_instances_pricing[0]['price']
    if is_empty(instance_price):
        return 0
    return filtered_instances_pricing[0]['price']

def get_provider_available_instances(provider):
    provider_instances_config = get_provider_infos(provider, 'instance_configs')
    region_instances = []
    for instance_config in provider_instances_config:
        region = instance_config['region']
        zones = instance_config['zones']
        available_zones = []
        for zone in zones:
            instances_types = get_provider_available_instances_by_region_zone(provider, region, zone['name'])
            if len(instances_types)>0:
                available_zones.append(zone['name'])
        if len(available_zones)>0:
            region_instances.append({"region": region, "zones": available_zones})

    return region_instances

def get_provider_available_instances_config_by_region_zone(provider, region, zone):
    instances_configs = get_provider_infos(provider, 'instance_configs')
    region_instances_configs = [config for config in instances_configs if config['region'] == region]
    if not len(region_instances_configs)>0:
        raise HTTPError("instance_in_region_not_found", 404, 'instance in this region not found', hdrs = {"i18n_code": "instance_in_region_not_found"}, fp = None)
    zone_instances_configs = [config for config in region_instances_configs[0]['zones'] if str(config['name']) == str(zone)]
    if not len(zone_instances_configs)>0:
        raise HTTPError("instance_type_in_zone_not_found", 404, 'instance type in this zone not found', hdrs = {"i18n_code": "instance_type_in_zone_not_found"}, fp = None)

    filtered_instances = [instance for instance in zone_instances_configs[0]['instance_types'] if'disabled' not in instance or not instance['disabled'] and os.getenv(instance['price_variable'])]
    return list(filtered_instances)

def get_provider_available_instances_by_region_zone(provider, region, zone):
    instances_configs = get_provider_infos(provider, 'instance_configs')
    region_instances_configs = [config for config in instances_configs if config['region'] == region]
    if not len(region_instances_configs)>0:
        raise HTTPError("instance_in_region_not_found", 404, 'instance in this region not found', hdrs = {"i18n_code": "instance_in_region_not_found"}, fp = None)
    zone_instances_configs = [config for config in region_instances_configs[0]['zones'] if str(config['name']) == str(zone)]
    if not len(zone_instances_configs)>0:
        raise HTTPError("instance_type_in_zone_not_found", 404, 'instance type in this zone not found', hdrs = {"i18n_code": "instance_type_in_zone_not_found"}, fp = None)

    filtered_instances = [instance for instance in zone_instances_configs[0]['instance_types'] if 'disabled' not in instance or not instance['disabled'] and os.getenv(instance['price_variable'])]
    return [instance['type'] for instance in filtered_instances]

def get_specific_config(provider, key, region, zone):
    config = None
    provider_instances_config = get_provider_infos(provider, 'instance_configs')
    for instance_config in provider_instances_config:
        if instance_config['region'] == region:
            for z in instance_config['zones']:
                if z['name'] == zone:
                    config = z.get(key, None)
                    break

    log_msg("INFO", "[provider][get_specific_config] provider = {}, key = {}, region = {}, zone = {} = > config = {}".format(provider, key, region, zone, config))
    return config

def get_provider_instances_pricing(provider):
    provider_instances_config = get_provider_infos(provider, 'instance_configs')
    region_instances = []
    for instance_config in provider_instances_config:
        region = instance_config['region']
        zones = instance_config['zones']
        available_zones = []
        for zone in zones:
            instances_types = get_provider_available_instances_by_region_zone(provider, region, zone['name'])
            if len(instances_types)>0:
                available_zones.append({'name':zone['name'], 'instances':zone['instance_types']})
        if len(available_zones)>0:
            region_instances.append({"region": region, "zones": available_zones})

    return region_instances

def get_provider_instances_pricing_by_region_zone(provider, region, zone):
    instances_configs = get_provider_infos(provider, 'instance_configs')
    region_instances_configs = [config for config in instances_configs if config['region'] == region]
    if not len(region_instances_configs)>0:
        raise HTTPError("instance_in_region_not_found", 404, 'instance in this region not found', hdrs = {"i18n_code": "instance_in_region_not_found"}, fp = None)
    zone_instances_configs = [config for config in region_instances_configs[0]['zones'] if str(config['name']) == str(zone)]
    if not len(zone_instances_configs)>0:
        raise HTTPError("instance_type_in_zone_not_found", 404, 'instance type in this zone not found', hdrs = {"i18n_code": "instance_type_in_zone_not_found"}, fp = None)
    filtered_instances = [instance for instance in zone_instances_configs[0]['instance_types'] if 'disabled' not in instance or not instance['disabled'] and os.getenv(instance['price_variable'])]
    return [{
        "name": instance['type'],
        "price": os.getenv(instance['price_variable'])
    } for instance in filtered_instances]

def extract_provider_name(driver):
    return driver.replace("Driver", "").lower()

def get_provider_dns_zones(provider):
    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'cloud_environments.yml'))
    result = []
    with open(config_path, "r") as stream:
        loaded_data = yaml.safe_load(stream)
        dns_zones = loaded_data['dns_zones']
        result = [dns_zone['name'] for dns_zone in dns_zones if extract_provider_name(dns_zone['driver']) == provider]
    return result

def get_dns_providers():
    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'cloud_environments.yml'))
    result = []
    with open(config_path, "r") as stream:
        loaded_data = yaml.safe_load(stream)
        dns_zones = loaded_data['dns_zones']
        result = list({extract_provider_name(dns_zone['driver']) for dns_zone in dns_zones})
    return result
