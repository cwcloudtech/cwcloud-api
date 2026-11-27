import os
import re

from utils.common import is_not_empty, is_true

# Pulumi project mode rejects project names outside [a-zA-Z0-9_.-] (e.g. an email
# used for buckets/registries): sanitized unless PULUMI_SANITIZE_PROJECT_NAME=false.
_sanitize_project_name = os.getenv('PULUMI_SANITIZE_PROJECT_NAME', 'true')
_allowed_chars_pattern = re.compile(r'[^a-zA-Z0-9_\-\.]')

def sanitize_project_name(name: str):
    return re.sub(_allowed_chars_pattern, '_', name) if is_true(_sanitize_project_name) else name

def convert_instance_state(switcher, server):
    if 'state' in server and is_not_empty(server['state']) and server['state'].lower() in switcher:
        return switcher.get(server['state'].lower())
    else:
        return "starting"
