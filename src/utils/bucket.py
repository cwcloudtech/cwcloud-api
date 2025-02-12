import os
import importlib

from minio import Minio
from time import sleep

from entities.Bucket import Bucket

from utils.common import is_empty
from utils.logger import log_msg
from utils.observability.cid import get_current_cid
from utils.provider import get_driver
from utils.constants import MAX_RETRY, WAIT_TIME

def register_bucket(hash, provider, region, chosen_user_id, current_user_id, bucket_name, bucket_type, db):
    from entities.Bucket import Bucket
    new_bucket = Bucket()
    new_bucket.hash = hash
    new_bucket.name = bucket_name
    new_bucket.type = bucket_type
    new_bucket.bucket_user_id = chosen_user_id
    new_bucket.user_id = current_user_id
    new_bucket.region = region
    new_bucket.provider = provider
    new_bucket.save(db)
    return new_bucket

def delete_bucket(provider, bucket, user_email, retry = 0):
    try:
        if retry >= MAX_RETRY:
            log_msg("WARN", "[delete_bucket] max retries has been reached : provider = {}, bucket = {}, user_email = {}".format(provider, bucket, user_email))
            return

        if retry > 0:
            waiting_time = WAIT_TIME * retry
            log_msg("DEBUG", "[delete_bucket] waiting: provider = {}, bucket = {}, user_email = {}, wait = {}".format(provider, bucket, user_email, waiting_time))
            sleep(waiting_time)

        ProviderDriverModule = importlib.import_module('drivers.{}'.format(get_driver(provider)))
        ProviderDriver = getattr(ProviderDriverModule, get_driver(provider))
        ProviderDriver().delete_bucket(bucket, user_email)
    except Exception as e:
        log_msg("WARN", "[delete_bucket] trying again because of this error: provider = {}, bucket = {}, user_email = {}, error = {}".format(provider, bucket, user_email, e))
        delete_bucket(provider, bucket, user_email, retry + 1)

def update_credentials(provider, bucket, db):
    ProviderDriverModule = importlib.import_module('drivers.{}'.format(get_driver(provider)))
    ProviderDriver = getattr(ProviderDriverModule, get_driver(provider))
    result = ProviderDriver().update_bucket_credentials(bucket)
    Bucket.updateCredentials(bucket.id, result["access_key"], result["secret_key"], db)

def refresh_bucket(user_email, provider, bucket_id, hashed_bucket_name, db):
    ProviderDriverModule = importlib.import_module('drivers.{}'.format(get_driver(provider)))
    ProviderDriver = getattr(ProviderDriverModule, get_driver(provider))
    result = ProviderDriver().refresh_bucket(user_email, hashed_bucket_name)
    if "type" in result:
        Bucket.updateType(bucket_id, result['type'], db)

def create_bucket(provider, user_email, bucket_id, hashed_bucket_name, region, bucket_type, db):
    ProviderDriverModule = importlib.import_module('drivers.{}'.format(get_driver(provider)))
    ProviderDriver = getattr(ProviderDriverModule, get_driver(provider))
    result = ProviderDriver().create_bucket(user_email, hashed_bucket_name, region, bucket_type)
    log_msg("DEBUG", "[create_bucket] driver result = {}".format(result))
    Bucket.update(bucket_id, result['endpoint'], result['user_id'] if "user_id" in result else None, result['access_key'], result['secret_key'], "active", db)

access_key = os.getenv('SCW_ACCESS_KEY')
secret_key = os.getenv('SCW_SECRET_KEY')
bucket_region = os.getenv('BUCKET_REGION')

invoice_bucket_url = os.getenv('BUCKET_URL')
invoice_bucket_name = os.getenv('BUCKET_NAME')

attachment_bucket_url = os.getenv('ATTACHMENT_BUCKET_URL', invoice_bucket_url)
attachment_bucket_name = os.getenv('ATTACHMENT_BUCKET_NAME', invoice_bucket_name)

def upload_to_attachment_bucket(path_file, target_name):
    return upload_bucket(path_file, target_name, attachment_bucket_url, attachment_bucket_name)

def download_from_attachment_bucket(path_file, target_name):
    return download_from_bucket(path_file, target_name, attachment_bucket_url, attachment_bucket_name)

def delete_from_attachment_bucket(path_file):
    return delete_from_bucket(path_file, attachment_bucket_url, attachment_bucket_name)

def upload_bucket(path_file, target_name, url, bucket_name):
    if any(is_empty(setting) for setting in [url, access_key, secret_key, bucket_name, bucket_region]):
        return {
            'status': 'ko',
            'error': 'Bucket settings are not configured',
            'i18n_code': 'bucket_settings_not_configured',
            'http_code': 405,
            'cid': get_current_cid()
        }

    if not os.path.exists(path_file):
        basename = os.path.basename(path_file)
        if not os.path.exists(basename):
           log_msg("ERROR", "[upload_bucket] file not exists: path_file = {}, basename = {}, target_name = {}".format(path_file, basename, target_name))
           return {
                'status': 'ko',
                'error': 'File not exists',
                'i18n_code': 'file_not_found',
                'http_code': 404,
                'cid': get_current_cid()
            }

        log_msg("DEBUG", "[upload_bucket] file not exists, switching path_file = {} with basename = {}".format(path_file, basename))
        target_name = path_file
        path_file = basename

    client = Minio(url, region = bucket_region, access_key = access_key, secret_key = secret_key)
    found = client.bucket_exists(bucket_name)
    log_msg("DEBUG", "[upload_bucket] found = {}".format(found))

    try:
        if not found:
            client.make_bucket(bucket_name)

        client.fput_object(bucket_name, target_name, path_file)
    except Exception as e:
        log_msg("ERROR", "[upload_bucket] unexpected error when uploading path_file = {} into bucket_name = {} e.type = {}, e.msg = {}".format(path_file, bucket_name, type(e), e))
        return {
            'status': 'ko',
            'error': "bucket upload error",
            'i18n_code': 'bucket_upload_error',
            'http_code': 500,
            'cid': get_current_cid()
        }

    return {
        'status': 'ok',
    }

def download_from_bucket(path_file, target_name, url, bucket_name):
    if any(is_empty(setting) for setting in [url, access_key, secret_key, bucket_name, bucket_region]):
        return {
            'status': 'ko',
            'error': 'Bucket settings are not configured',
            'i18n_code': 'bucket_settings_not_configured',
            'http_code': 405,
            'cid': get_current_cid()
        }

    try:
        client = Minio(url, region = bucket_region, access_key = access_key, secret_key = secret_key)
        client.fget_object(bucket_name, path_file, target_name)
        return {
            'status': 'ok',
        }
    except Exception as e:
        not_found_msg = "File not found: target_name = {}, path_file = {}".format(target_name, path_file)
        log_msg("WARN", "[bucket][download_from_bucket] {}, e.type = {}, e.msg = {}".format(not_found_msg, type(e), e))

        basename = os.path.basename(path_file)
        if basename != path_file:
           log_msg("INFO", "[bucket][download_from_bucket] switch file_path path_file = {} with basename = {}".format(path_file, basename))
           return download_from_bucket(basename, target_name, url, bucket_name)

        return {
            'status': 'ko',
            'error': not_found_msg,
            'i18n_code': 'file_not_found',
            'http_code': 404,
            'cid': get_current_cid()
        }

def delete_from_bucket(path_file, url, bucket_name):
    if any(is_empty(setting) for setting in [url, access_key, secret_key, bucket_name, bucket_region]):
        return {
            'status': 'ko',
            'error': 'Bucket settings are not configured',
            'i18n_code': 'bucket_settings_not_configured',
            'http_code': 405,
            'cid': get_current_cid()
        }

    try:
        client = Minio(url, region = bucket_region, access_key = access_key, secret_key = secret_key)
        client.remove_object(bucket_name, path_file)
        return {
            'status': 'ok',
        }
    except Exception as e:
        not_found_msg = "File not found: path_file = {}".format(path_file)
        log_msg("WARN", "[bucket][delete_from_bucket] {}, e.type = {}, e.msg = {}".format(not_found_msg, type(e), e))

        basename = os.path.basename(path_file)
        if basename != path_file:
           log_msg("INFO", "[bucket][delete_from_bucket] switch file_path path_file = {} with basename = {}".format(path_file, basename))
           return delete_from_bucket(basename, url, bucket_name)

        return {
            'status': 'ko',
            'error': not_found_msg,
            'i18n_code': 'file_not_found',
            'http_code': 404,
            'cid': get_current_cid()
        }
