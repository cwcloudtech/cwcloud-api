from sqlalchemy import text

from utils.common import is_not_empty_key, is_true

ALL_FLAGS = [
    'without_vat',
    'auto_pay',
    'daasapi',
    'emailapi',
    'disable_emails',
    'cwaiapi',
    'faasapi',
    'k8sapi', 
    'iotapi',
    'monitorapi',
    'storageapi',
    'block'
]

def is_flag_enabled(vdict, key):
    return is_not_empty_key(vdict, key) and is_true(vdict[key])

def is_flag_disabled(vdict, key):
    return not is_flag_enabled(vdict, key)
