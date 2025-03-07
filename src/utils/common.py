import os
import re
import base64

from passlib.context import CryptContext

AUTOESCAPE_EXTENSIONS = ['html', 'xml']

pwd_context = CryptContext(schemes = ["bcrypt"], deprecated = "auto")

_src_path = "/app/src"

def get_src_path():
    return _src_path

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def generate_hash_password(password):
    return pwd_context.hash(password)

def is_boolean(var):
    if isinstance(var, bool):
        return True

    bool_chars = ["true", "false", "ok", "ko", "yes", "no"]
    return var is not None and any(c == "{}".format(var).lower() for c in bool_chars)

def is_not_empty(var):
    if isinstance(var, bool):
        return var
    elif isinstance(var, int) or isinstance(var, float):
        return not var == 0
    elif isinstance(var, list) or isinstance(var, dict):
        return len(var) > 0
    empty_chars = ["", "null", "nil", "false", "none", "undef", "undefined"]
    return var is not None and not any(c == "{}".format(var).lower() for c in empty_chars)

def is_true(var):
    if isinstance(var, bool):
        return var
    false_char = ["false", "ko", "no", "off"]
    return is_not_empty(var) and not any(c == "{}".format(var).lower() for c in false_char)

def is_false(var):
    return not is_true(var)

def is_empty(var):
    return not is_not_empty(var)

def is_empty_key(vdict, key):
    return is_empty(vdict) or key not in vdict or is_empty(vdict[key])

def is_not_empty_key(vdict, key):
    return not is_empty_key(vdict, key)

def del_key_if_exists(vdict, key):
    if is_not_empty_key(vdict, key):
        del vdict[key]

def is_numeric(var):
    if isinstance(var, int) or isinstance(var, float):
        return True

    return is_not_empty(var) and bool(re.match(r'^[0-9\.]+$', var))

def is_not_numeric(var):
    return not is_numeric(var)

def is_disabled(var):
    return is_empty(var) or "changeit" in var

def is_enabled(var):
    return not is_disabled(var)

def exists_entry(dictionary, key):
    return key in dictionary and is_not_empty(dictionary[key])

def safe_compare_entry(dictionary, key, expected_value):
    return exists_entry(dictionary, key) and is_not_empty(expected_value) and dictionary[key] == expected_value

def safe_contain_entry(dictionary, key, expected_contained_value):
    return exists_entry(dictionary, key) and is_not_empty(expected_contained_value) and expected_contained_value in dictionary[key]

def safe_get_entry(dictionary, key, default_value = None):
    return default_value if not exists_entry(dictionary, key) else dictionary[key]

def is_response_ok(code):
    return code >= 200 and code < 400

def is_response_ko(code):
    return not is_response_ok(code)

def is_duration_valid(duration):
    return is_not_empty(duration) and duration != -1

def unbase64(encoded_data):
    decoded_content = base64.b64decode(encoded_data)
    return decoded_content.decode('utf-8')

def is_uuid(var):
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89a-bA-B][0-9a-f]{3}-[0-9a-f]{12}$'
    return bool(re.match(pattern, var))

def is_not_uuid(var):
    return not is_uuid(var)
   
def to_camel_case(name):
   return ''.join(word.title() if index_word > 0 else word for index_word, word in enumerate(name.split('_')))

def convert_dict_keys_to_camel_case(data):
   if isinstance(data, dict):
       return {to_camel_case(key): convert_dict_keys_to_camel_case(value) for key, value in data.items()}
   elif isinstance(data, list):
       return [convert_dict_keys_to_camel_case(item) for item in data]
   else:
       return data

def get_admin_status(current_user):
    if is_empty(current_user):
        return False
    else:
        return current_user.is_admin

def get_env_int(var_name, default = None):
    value = os.getenv(var_name)
    return int(value) if is_numeric(value) else default

def get_env_float(var_name, default = None):
    value = os.getenv(var_name)
    return float(value) if is_numeric(value) else default 

def get_env_bool(var_name, default = None):
    return is_true(os.getenv(var_name, is_true(default)))

_allowed_chars_metric_pattern = re.compile(r'[^a-zA-Z0-9]')
def sanitize_metric_name(name: str):
    return re.sub(_allowed_chars_metric_pattern, '_', name)

def get_or_else(vdict, key, default):
    return default if is_empty_key(vdict, key) else vdict[key]

def sanitize_header_name(name: str) -> str:
    return '-'.join(word.capitalize() for word in name.split('-'))

def is_http_status_code(status_code: str) -> bool:
    if not isinstance(status_code, str) or len(status_code) != 3:
        return False
    if status_code.endswith('*'):
        try:
            first_two = int(status_code[:2])
            return 10 <= first_two <= 59
        except ValueError:
            return False
    try:
        status = int(status_code)
        return 100 <= status <= 599
    except ValueError:
        return False

def is_not_http_status_code(status_code: str) -> bool:
    return not is_http_status_code(status_code)
