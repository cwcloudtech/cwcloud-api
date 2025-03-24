import json
import time
import asyncio
import requests

from datetime import datetime

from adapters.AdapterConfig import get_adapter
from entities.faas.Function import FunctionEntity
from entities.faas.Invocation import InvocationEntity
from entities.faas.InvocationExecutionTrace import InvocationExecutionTraceEntity

from utils.common import del_key_if_exists, get_env_int, is_empty, is_false, is_not_empty, is_not_empty_key, is_not_numeric, is_not_uuid, is_true
from utils.consumer import CONSUMER_CHANNEL, CONSUMER_GROUP
from utils.encoder import AlchemyEncoder
from utils.faas.invocations import _in_progress, is_unknown_state
from utils.faas.functions import is_not_owner
from utils.faas.invoker import get_email_invoker, get_invoker_id, override_invoker_id
from utils.faas.iot import send_payload_in_realtime
from utils.http import HTTP_REQUEST_TIMEOUT
from utils.logger import log_msg
from utils.observability.cid import get_current_cid

_pubsub_adapter = get_adapter("pubsub")
_max_retry_invoke_sync = get_env_int('MAX_RETRY_INVOKE_SYNC', 100)
_invoke_sync_wait_time = get_env_int('INVOKE_SYNC_WAIT_TIME', 1)

def invoke(payload, current_user, user_auth, db):
    if is_empty(payload.content.state):
        payload.content.state = _in_progress

    if is_unknown_state(payload.content.state):
        return {
            'status': 'ko',
            'code': 400,
            'message': "State '{}' is not known".format(payload.content.state),
            'i18n_code': 'faas_state_not_known',
            'cid': get_current_cid()
        }
    
    if is_not_uuid(payload.content.function_id):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Invalid function id '{}' is not a valid UUID".format(payload.content.function_id),
            'i18n_code': 'faas_invalid_function_id',
            'cid': get_current_cid()
        }

    db_function = db.query(FunctionEntity).filter(FunctionEntity.id == payload.content.function_id)
    function = db_function.first()

    if not function:
        return {
            'status': 'ko',
            'code': 400,
            'message': "Function '{}' not found".format(id),
            'i18n_code': 'faas_not_found_function',
            'cid': get_current_cid()
        }
    
    if is_false(function.is_public) and is_not_owner(current_user, function):
        return {
            'status': 'ko',
            'code': 403,
            'message': "This function '{}' is not granted for you".format(function.id),
            'i18n_code': 'faas_not_exec_right',
            'cid': get_current_cid()
        }

    if len(function.content['args']) != len(payload.content.args):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Wrong number of arguments",
            'i18n_code': 'faas_wrong_args_number',
            'cid': get_current_cid()
        }

    if any(a.key not in function.content['args'] for a in payload.content.args):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Not the same arguments",
            'i18n_code': 'faas_not_same_args',
            'cid': get_current_cid()
        }

    new_invocation = InvocationEntity(**payload.dict())
    new_invocation_execution_trace = InvocationExecutionTraceEntity(**payload.dict())
    invoker_id = get_invoker_id(payload, current_user)
    if is_not_empty(invoker_id):
        new_invocation.invoker_id = invoker_id
        new_invocation_execution_trace.invoker_id = invoker_id

    db.add(new_invocation)
    db.commit()
    db.refresh(new_invocation)

    new_invocation_execution_trace.invocation_id = new_invocation.id
    db.add(new_invocation_execution_trace)
    db.commit()
    db.refresh(new_invocation_execution_trace)

    invocation_id = new_invocation.id
    payload.content.user_auth = user_auth
    _pubsub_adapter().publish(CONSUMER_GROUP, CONSUMER_CHANNEL, {'id': "{}".format(invocation_id), **payload.dict()})

    return {
        'status': 'ok',
        'code': 202,
        'id': invocation_id,
        'created_at': new_invocation.created_at,
        'updated_at': new_invocation.updated_at
    }

def is_state_exists(search_result_invocation):
    return is_not_empty_key(search_result_invocation, 'entity') and is_not_empty(search_result_invocation['entity'].content) and is_not_empty_key(search_result_invocation['entity'].content, 'state')

def invoke_sync(payload, current_user, user_auth, db):
    result = invoke(payload, current_user, user_auth, db)
    if is_false(result['status']):
        return result

    id = result['id']
    for retry in range(0, _max_retry_invoke_sync):
        search_result_invocation = get_invocation(id, current_user, db)

        state = search_result_invocation['entity'].content['state'] if is_state_exists(search_result_invocation) else "undefined"
        log_msg("DEBUG", "[invoke_sync] found invocation: id = {}, retry = {}, status = {}, state = {}".format(id, retry, search_result_invocation['status'], state))

        if is_false(search_result_invocation['status']) or state != _in_progress:
            return search_result_invocation

        time.sleep(_invoke_sync_wait_time)

    return search_result_invocation

async def async_send_payload_in_realtime(callback, safe_payload):
    await send_payload_in_realtime(callback, safe_payload)

def send_result_to_callbacks(payload, invocation, function):
    if payload.content.state != _in_progress:
        old_invocation_json = json.loads(json.dumps(invocation, cls = AlchemyEncoder))
        safe_payload = old_invocation_json.copy()
        del_key_if_exists(safe_payload['content'], 'env')
        del_key_if_exists(safe_payload['content'], 'user_auth')

        serverless_function = json.loads(json.dumps(function, cls = AlchemyEncoder))

        #? invoke legacy faas functions with http callbacks
        if is_not_empty_key(serverless_function['content'], 'callback_url'):
            callback_headers = { "Authorization": serverless_function['content']['callback_authorization_header'], "Content-Type": "application/json" } if is_not_empty_key(serverless_function['content'], 'callback_authorization_header') else { "Content-Type": "application/json" }
            callback_url = serverless_function['content']['callback_url']
            log_msg("DEBUG", "[send_result_to_callbacks] invoke callback: {}".format(callback_url))
            requests.post(callback_url, json=safe_payload, headers=callback_headers, timeout=HTTP_REQUEST_TIMEOUT)
        else:
            if is_not_empty_key(serverless_function['content'], 'callbacks'):
                callbacks = serverless_function['content']['callbacks']
                for callback in callbacks:
                    if is_not_empty_key(callback, 'endpoint'):
                        if callback['type'] == "http":
                            callback_headers = { "Authorization": callback['token'], "Content-Type": "application/json" } if is_not_empty_key(callback, 'token') else { "Content-Type": "application/json" }
                            log_msg("INFO", f"[send_result_to_callbacks] invoke callback: type={callback['type']}, endpoint={callback['endpoint']}")
                            requests.post(callback['endpoint'], json=safe_payload, headers=callback_headers, timeout=HTTP_REQUEST_TIMEOUT)
                        elif callback['type'] == "websocket" or callback['type'] == "mqtt":
                            log_msg("INFO", f"[send_result_to_callbacks] invoke callback: type={callback['type']}, endpoint={callback['endpoint']}")
                            asyncio.run(async_send_payload_in_realtime(callback, safe_payload))

def complete(id, payload, current_user, db):
    if is_empty(payload.content.state):
        return {
            'status': 'ko',
            'code': 400,
            'message': "State is mandatory",
            'i18n_code': 'faas_state_undefined',
            'cid': get_current_cid()
        }

    if is_unknown_state(payload.content.state):
        return {
            'status': 'ko',
            'code': 400,
            'message': "State '{}' is not known".format(payload.content.state),
            'i18n_code': 'faas_state_not_known',
            'cid': get_current_cid()
        }

    db_invocation = db.query(InvocationEntity).filter(InvocationEntity.id == id)
    db_trace_invocation = db.query(InvocationExecutionTraceEntity).filter(InvocationExecutionTraceEntity.invocation_id == id)
    old_invocation = db_invocation.first()
    if not old_invocation:
        return {
            'status': 'ko',
            'code': 404,
            'message': "Resource '{}' not found".format(id),
            'i18n_code': 'faas_not_found_invocation',
            'cid': get_current_cid()
        }
    
    if is_not_uuid(payload.content.function_id):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Invalid function id '{}' is not a valid UUID".format(payload.content.function_id),
            'i18n_code': 'faas_invalid_function_id',
            'cid': get_current_cid()
        }

    db_function = db.query(FunctionEntity).filter(FunctionEntity.id == payload.content.function_id)
    function = db_function.first()

    if not function:
        return {
            'status': 'ko',
            'code': 400,
            'message': "Function '{}' not found".format(id),
            'i18n_code': 'faas_not_found_function',
            'cid': get_current_cid()
        }

    if len(function.content['args']) != len(payload.content.args):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Wrong number of arguments",
            'i18n_code': 'faas_wrong_args_number',
            'cid': get_current_cid()
        }
    
    if any(a.key not in function.content['args'] for a in payload.content.args):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Not the same arguments",
            'i18n_code': 'faas_not_same_args',
            'cid': get_current_cid()
        }

    if is_not_owner(current_user, function):
        return {
            'status': 'ko',
            'code': 403,
            'message': "This function '{}' is not granted for you".format(function.id),
            'i18n_code': 'faas_not_exec_right',
            'cid': get_current_cid()
        }

    result = override_invoker_id(payload, old_invocation, current_user, db)
    if is_false(result['status']):
        return result

    updated_at = datetime.now()
    db_invocation.update({
        "invoker_id": result['invoker_id'],
        "content": payload.content.dict(),
        "updated_at": updated_at
    })
    db.commit()

    db_trace_invocation.update({
        "invoker_id": result['invoker_id'],
        "content": payload.content.dict(),
        "updated_at": updated_at
    })
    db.commit()

    send_result_to_callbacks(payload, old_invocation, function)

    return {
        'status': 'ok',
        'code': 200,
        'id': id,
        'updated_at': updated_at
    }

def get_invocation(id, current_user, db):
    if is_true(current_user.is_admin):
        invocation = db.query(InvocationEntity).filter(InvocationEntity.id == id)
    else:
        invocation = db.query(InvocationEntity).filter(InvocationEntity.id == id, InvocationEntity.invoker_id == current_user.id)

    db_invocation = invocation.first()
    if not db_invocation:
        return {
            'status': 'ko',
            'code': 404,
            'message': "Resource '{}' not found".format(id),
            'i18n_code': 'faas_not_found_invocation',
            'cid': get_current_cid()
        }

    db.refresh(db_invocation)
    return {
        'status': 'ok',
        'code': 200,
        'entity': db_invocation
    }

def delete_invocation(id, current_user, db):
    if is_true(current_user.is_admin):
        invocation = db.query(InvocationEntity).filter(InvocationEntity.id == id)
    else:
        invocation = db.query(InvocationEntity).filter(InvocationEntity.id == id, InvocationEntity.invoker_id == current_user.id)

    if invocation.first():
        invocation.delete(synchronize_session=False)
        db.commit()
    return {
        'status': 'ok',
        'code': 200
    }

def clear_my_invocations(current_user, db):
    db.query(InvocationEntity).filter(InvocationEntity.invoker_id == current_user.id).delete()
    db.commit()
    return {
        'status': 'ok',
        'code': 200
    }

def get_my_invocations(db, current_user, start_index, max_results):
    if is_not_numeric(start_index) or is_not_numeric(max_results):
        return {
            'status': 'ko',
            'code': 400,
            'message': 'Not valid parameters start_index or max_results (not numeric)',
            'i18n_code': 'faas_invalid_parameters',
            'cid': get_current_cid()
        }

    results = db.query(InvocationEntity).filter(InvocationEntity.invoker_id == current_user.id).order_by(InvocationEntity.updated_at.desc()).order_by(InvocationEntity.created_at.desc()).offset(int(start_index)).limit(int(max_results)).all()

    return {
        'status': 'ok',
        'code': 200,
        'start_index': start_index,
        'max_results': max_results,
        'results': results
    }

def get_all_invocations(db, current_user, start_index, max_results):
    if is_false(current_user.is_admin):
        return {
            'status': 'ko',
            'code': 403,
            'message': 'You need to be an administrator',
            'i18n_code': 'faas_not_admin',
            'cid': get_current_cid()
        }

    if is_not_numeric(start_index) or is_not_numeric(max_results):
        return {
            'status': 'ko',
            'code': 400,
            'message': 'Not valid parameters start_index or max_results (not numeric)',
            'i18n_code': 'faas_invalid_parameters',
            'cid': get_current_cid()
        }

    results = db.query(InvocationEntity).order_by(InvocationEntity.updated_at.desc()).order_by(InvocationEntity.created_at.desc()).offset(int(start_index)).limit(int(max_results)).all()

    return {
        'status': 'ok',
        'code': 200,
        'start_index': start_index,
        'max_results': max_results,
        'results': list(map(lambda i: {
            "id": i.id,
            "content": i.content,
            "created_at": i.created_at,
            "updated_at": i.updated_at,
            "invoker": {
                "id": i.invoker_id,
                "username": get_email_invoker(i, db)
            }
        }, results))
    }
