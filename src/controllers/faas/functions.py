import json
import copy

from datetime import datetime
from fastapi.responses import JSONResponse

from entities.faas.Function import FunctionEntity

from utils.common import is_empty, is_false, is_not_empty, is_not_numeric, is_true
from utils.faas.functions import is_not_supported_language, is_not_supported_callback_type, restructure_callbacks
from utils.faas.owner import get_email_owner, get_owner_id, override_owner_id
from utils.faas.security import has_not_exec_right, has_not_write_right
from utils.encoder import AlchemyEncoder
from utils.file import get_b64_content
from utils.observability.cid import get_current_cid

def add_function(payload, current_user, db):
    if is_empty(payload.content.name):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Function name is missing",
            'i18n_code': 'faas_function_name_missing',
            'cid': get_current_cid()
        }

    if is_not_supported_language(payload.content.language):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Programing language '{}' is not supported".format(payload.content.language),
            'i18n_code': 'faas_language_not_supported',
            'cid': get_current_cid()
        }
    
    if is_not_empty(payload.content.callbacks):
        for callback in payload.content.callbacks:
            if is_not_supported_callback_type(callback.type):
                return {
                    'status': 'ko',
                    'code': 400,
                    'message': "Callback type '{}' is not supported".format(callback.type),
                    'i18n_code': 'faas_callback_type_not_supported'
                }

    payload.owner_id = get_owner_id(payload, current_user)
    payload.is_public = is_true(payload.is_public)
    new_function = FunctionEntity(**payload.dict())
    db.add(new_function)
    db.commit()
    db.refresh(new_function)

    return {
        'status': 'ok',
        'code': 201,
        'id': new_function.id,
        'created_at': new_function.created_at,
        'updated_at': new_function.updated_at
    }

def override_function(id, payload, current_user, db):
    db_function = db.query(FunctionEntity).filter(FunctionEntity.id == id)
    old_function = db_function.first()
    if not old_function:
        return {
            'status': 'ko',
            'code': 404,
            'message': "Resource '{}' not found".format(id),
            'i18n_code': 'not_found',
            'cid': get_current_cid()
        }

    if has_not_write_right(current_user, old_function):
        return {
            'status': 'ko',
            'code': 403,
            'message': "You have no write right on '{}' function".format(id),
            'i18n_code': 'faas_not_write_right',
            'cid': get_current_cid()
        }

    if is_not_supported_language(payload.content.language):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Programing language '{}' is not supported".format(payload.content.language),
            'i18n_code': 'faas_language_not_supported',
            'cid': get_current_cid()
        }
    
    if is_not_empty(payload.content.callbacks):
        for callback in payload.content.callbacks:
            if is_not_supported_callback_type(callback.type):
                return {
                    'status': 'ko',
                    'code': 400,
                    'message': "Callback type '{}' is not supported".format(callback.type),
                    'i18n_code': 'faas_callback_type_not_supported'
                }

    updated_at = datetime.now()
    result = override_owner_id(payload, old_function, current_user, db)
    if is_false(result['status']):
        return result

    db_function.update({
        "owner_id": result['owner_id'],
        "is_public": is_true(payload.is_public),
        "is_protected": is_true(payload.is_protected),
        "content": payload.content.dict(),
        "updated_at": updated_at
    })
    db.commit()

    return {
        'status': 'ok',
        'code': 200,
        'id': id,
        'updated_at': updated_at
    }

def get_function(id, current_user, db):
    function = db.query(FunctionEntity).filter(FunctionEntity.id == id)

    db_function = function.first()
    if not db_function:
        return {
            'status': 'ko',
            'code': 404,
            'message': "Resource '{}' not found".format(id),
            'i18n_code': 'not_found'
        }
    
    if has_not_exec_right(current_user, db_function):
        return {
            'status': 'ko',
            'code': 403,
            'message': "You have no exec right on '{}' function".format(id),
            'i18n_code': 'faas_not_exec_right'
        }
    
    content = copy.deepcopy(db_function.content)
    db_function.content = restructure_callbacks(content)

    return {
        'status': 'ok',
        'code': 200,
        'entity': db_function
    }

def delete_function(id, current_user, db):
    function = db.query(FunctionEntity).filter(FunctionEntity.id == id)
    db_function = function.first()
    if db_function:
        if has_not_write_right(current_user, db_function):
            return {
                'status': 'ko',
                'code': 403,
                'message': "You have no write right on '{}' function".format(id),
                'i18n_code': 'faas_not_write_right'
            }
            
        if is_true(db_function.is_protected):
            return {
                'status': 'ko',
                'code': 403,
                'message': "You cannot delete a protected function",
                'i18n_code': 'faas_function_protected'
            }
    
        function.delete(synchronize_session=False)
        db.commit()
    return {
        'status': 'ok',
        'code': 200
    }

def get_my_functions(db, current_user, start_index, max_results):
    if is_not_numeric(start_index) or is_not_numeric(max_results):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Not valid parameters start_index or max_results (not numeric)",
            'i18n_code': 'faas_invalid_parameters'
        }

    results = db.query(FunctionEntity).filter(FunctionEntity.owner_id == current_user.id).order_by(FunctionEntity.updated_at.desc()).order_by(FunctionEntity.created_at.desc()).offset(int(start_index)).limit(int(max_results)).all()

    for function in results:
        content = copy.deepcopy(function.content)
        function.content = restructure_callbacks(content)
        
    return {
        'status': 'ok',
        'code': 200,
        'start_index': start_index,
        'max_results': max_results,
        'results': results
    }

def get_all_functions(db, current_user, start_index, max_results):
    if is_false(current_user.is_admin):
        return {
            'status': 'ko',
            'code': 403,
            'message': "You need to be an administrator",
            'i18n_code': 'faas_not_exec_right'
        }

    if is_not_numeric(start_index) or is_not_numeric(max_results):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Not valid parameters start_index or max_results (not numeric)",
            'i18n_code': 'faas_invalid_parameters'
        }

    results = db.query(FunctionEntity).order_by(FunctionEntity.updated_at.desc()).order_by(FunctionEntity.created_at.desc()).offset(int(start_index)).limit(int(max_results)).all()

    for function in results:
        content = copy.deepcopy(function.content)
        function.content = restructure_callbacks(content)

    return {
        'status': 'ok',
        'code': 200,
        'start_index': start_index,
        'max_results': max_results,
        'results': list(map(lambda f: {
            "id": f.id,
            "is_public": f.is_public,
            "content": f.content,
            "created_at": f.created_at,
            "updated_at": f.updated_at,
            "owner": {
                "id": f.owner_id,
                "username": get_email_owner(f, db)
            }
        }, results))
    }
    
def export_function(id, db):
    function = db.query(FunctionEntity).filter(FunctionEntity.id == id).first()
    if not function:
        return JSONResponse(content = { 
            'status': 'ko',
            'code': 404,
            'message': "Resource '{}' not found".format(id),
            'i18n_code': 'not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    content = copy.deepcopy(function.content)
    function.content = restructure_callbacks(content)
    function_dict = json.loads(json.dumps(function, cls = AlchemyEncoder))
    function_json = json.dumps(function_dict, indent=4)

    file_name = "function-{}.json".format(function.content["name"])
    with open(file_name, "w") as outfile:
        outfile.write(function_json)

    encoded_string = get_b64_content(file_name, True)
    return JSONResponse(content = {"file_name": file_name, "blob": str(encoded_string)}, status_code = 200)

def import_new_function(current_user, function_file, db):
    function_json = function_file.file.read()
    function_dict = json.loads(function_json)
    
    new_function = FunctionEntity()
    new_function.owner_id = current_user.id
    new_function.is_public = function_dict["is_public"]
    new_function.content = function_dict["content"]
    db.add(new_function)
    db.commit()

    function_json = json.loads(json.dumps(new_function, cls = AlchemyEncoder))
    function_json["id"] = str(new_function.id)
    return JSONResponse(content = function_json, status_code = 200)
