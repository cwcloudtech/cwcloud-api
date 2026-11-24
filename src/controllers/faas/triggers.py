from datetime import datetime
from croniter import croniter
from adapters.AdapterConfig import get_adapter

from entities.faas.Function import FunctionEntity
from entities.faas.Trigger import TriggerEntity
from utils.common import is_empty, is_false, is_not_empty, is_not_numeric, is_true
from utils.consumer import TRIGGERS_CHANNEL, TRIGGERS_GROUP
from utils.date import is_iso_date_valid
from utils.faas.functions import is_not_owner
from utils.faas.owner import get_email_owner, get_owner_id, override_owner_id
from utils.faas.triggers import is_not_supported_kind
from utils.observability.cid import get_current_cid

_pubsub_adapter = get_adapter("pubsub")

def add_trigger(payload, current_user, db):
    if is_not_supported_kind(payload.kind):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Trigger kind '{}' is not supported".format(payload.kind),
            'i18n_code': 'faas_trigger_kind_not_supported',
            'cid': get_current_cid()
        }

    payload.kind = payload.kind.lower()
    if payload.kind == "cron" and (is_empty(payload.content.cron_expr) or not croniter.is_valid(payload.content.cron_expr)):
        return {
            'status': 'ko',
            'code': 400,
            'message': "The cron expr is invalid",
            'i18n_code': 'cron_expr_invalid',
            'cid': get_current_cid()
        }
    if payload.kind == "schedule":
        if is_empty(payload.content.execution_time):
            return {
                'status': 'ko',
                'code': 400,
                'message': 'The execution time is mandatory',
                'i18n_code': 'faas_execution_time_mandatory',
                'cid': get_current_cid()
            }
        elif is_iso_date_valid(payload.content.execution_time):
            return {
                'status': 'ko',
                'code': 400,
                'message': 'The execution time is not a valid ISO date',
                'i18n_code': 'faas_execution_time_invalid',
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
            'message': "You have no right to create a trigger on this function",
            'i18n_code': 'faas_not_granted',
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

    payload.owner_id = get_owner_id(payload, current_user)
    new_trigger = TriggerEntity(**payload.dict())
    db.add(new_trigger)
    db.commit()
    db.refresh(new_trigger)

    _pubsub_adapter().publish(TRIGGERS_GROUP, TRIGGERS_CHANNEL, {
        'action': 'add',
        'trigger': {
            'id': "{}".format(new_trigger.id),
            'created_at': "{}".format(new_trigger.created_at),
            'updated_at': "{}".format(new_trigger.updated_at)
        }
    })

    return {
        'status': 'ok',
        'code': 201,
        'id': new_trigger.id,
        'created_at': new_trigger.created_at,
        'updated_at': new_trigger.updated_at
    }

def override_trigger(id, current_user, payload, db):
    if is_true(current_user.is_admin):
        db_trigger = db.query(TriggerEntity).filter(TriggerEntity.id == id)
    else:
        db_trigger = db.query(TriggerEntity).filter(TriggerEntity.id == id, TriggerEntity.owner_id == current_user.id)

    old_trigger = db_trigger.first()
    if not old_trigger:
        return {
            'status': 'ko',
            'code': 404,
            'message': "Resource '{}' not found".format(id),
            'i18n_code': 'faas_not_found_trigger',
            'cid': get_current_cid()
        }

    if is_not_supported_kind(payload.kind):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Trigger kind '{}' is not supported".format(payload.kind),
            'i18n_code': 'faas_trigger_kind_not_supported',
            'cid': get_current_cid()
        }

    payload.kind = payload.kind.lower()
    if payload.kind == "cron" and (is_empty(payload.content.cron_expr) or not croniter.is_valid(payload.content.cron_expr)):
        return {
            'status': 'ko',
            'code': 400,
            'message': "The cron expr is invalid",
            'i18n_code': 'cron_expr_invalid',
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

    result = override_owner_id(payload, old_trigger, current_user, db)
    if is_false(result['status']):
        return result

    updated_at = datetime.now()
    db_trigger.update({
        "owner_id": result['owner_id'],
        "kind": payload.kind,
        "content": payload.content.dict(),
        "updated_at": updated_at
    })
    db.commit()

    _pubsub_adapter().publish(TRIGGERS_GROUP, TRIGGERS_CHANNEL, {
        'action': 'override',
        'trigger': {
            'id': "{}".format(id),
            'updated_at': "{}".format(updated_at)
        }
    })

    return {
        'status': 'ok',
        'code': 200,
        'id': id,
        'updated_at': updated_at
    }

def get_trigger(id, current_user, db):
    if is_true(current_user.is_admin):
        trigger = db.query(TriggerEntity).filter(TriggerEntity.id == id)
    else:
        trigger = db.query(TriggerEntity).filter(TriggerEntity.id == id, TriggerEntity.owner_id == current_user.id)

    if not trigger.first():
        return {
            'status': 'ko',
            'code': 404,
            'message': "Resource '{}' not found".format(id),
            'i18n_code': 'faas_not_found_trigger',
            'cid': get_current_cid()
        }

    return {
        'status': 'ok',
        'code': 200,
        'entity': trigger.first()
    }

def delete_trigger(id, current_user, db):
    if is_true(current_user.is_admin):
        trigger = db.query(TriggerEntity).filter(TriggerEntity.id == id)
    else:
        trigger = db.query(TriggerEntity).filter(TriggerEntity.id == id, TriggerEntity.owner_id == current_user.id)

    if trigger.first():
        trigger.delete(synchronize_session=False)
        db.commit()

    _pubsub_adapter().publish(TRIGGERS_GROUP, TRIGGERS_CHANNEL, {
        'action': 'delete',
        'trigger': {
            'id': "{}".format(id)
        }
    })

    return {
        'status': 'ok',
        'code': 200
    }

def get_my_triggers(db, current_user, kind, start_index, max_results):
    if is_not_numeric(start_index) or is_not_numeric(max_results):
        return {
            'status': 'ko',
            'code': 400,
            'message': 'Not valid parameters start_index or max_results (not numeric)',
            'i18n_code': 'faas_invalid_parameters',
            'cid': get_current_cid()
        }
    
    if is_not_empty(kind):
        query = db.query(TriggerEntity).filter(TriggerEntity.kind == kind.lower(), TriggerEntity.owner_id == current_user.id)
    else:
        query = db.query(TriggerEntity).filter(TriggerEntity.owner_id == current_user.id)

    results = query.order_by(TriggerEntity.updated_at.desc()).order_by(TriggerEntity.created_at.desc()).offset(int(start_index)).limit(int(max_results)).all()

    return {
        'status': 'ok',
        'code': 200,
        'start_index': start_index,
        'max_results': max_results,
        'results': results
    }

def get_all_triggers(db, current_user, kind, start_index, max_results):
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
    
    if is_not_empty(kind):
        query = db.query(TriggerEntity).filter(TriggerEntity.kind == kind.lower())
    else:
        query = db.query(TriggerEntity)

    results = query.order_by(TriggerEntity.updated_at.desc()).order_by(TriggerEntity.created_at.desc()).offset(int(start_index)).limit(int(max_results)).all()

    return {
        'status': 'ok',
        'code': 200,
        'start_index': start_index,
        'max_results': max_results,
        'results': [{
            "id": t.id,
            "kind": t.kind,
            "content": t.content,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
            "owner": {
                "id": t.owner_id,
                "username": get_email_owner(t, db)
            }
        } for t in results]
    }

def clear_my_triggers(current_user, db):
    db.query(TriggerEntity).filter(TriggerEntity.owner_id == current_user.id).delete()
    db.commit()

    _pubsub_adapter().publish(TRIGGERS_GROUP, TRIGGERS_CHANNEL, {
        'action': 'clear'
    })

    return {
        'status': 'ok',
        'code': 200
    }
