import os
import yaml

def get_firewall_tags():
    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'cloud_environments.yml'))
    result = []
    with open(config_path, "r") as stream:
        loaded_data = yaml.safe_load(stream)
        result = loaded_data.get('firewall_tags', [])
    return result
