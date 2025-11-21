from typing import Optional
from datetime import datetime
from entities.Monitor import Monitor
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from utils.common import is_empty, is_not_empty, is_not_http_status_code
from utils.observability.cid import get_current_cid
from utils.dynamic_name import generate_hashed_name
from utils.observability.monitor import not_match_tcp_url_format

def get_monitors(db, family: Optional[str] = None):
    monitors = Monitor.getAllMonitors(db)
    if is_not_empty(family):
        monitors = [monitor for monitor in monitors if monitor.family == family]
    return monitors

def get_monitor(monitor_id, db):
    monitor = Monitor.findMonitorById(monitor_id, db)
    if not monitor:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Monitor not found',
            'i18n_code': 'monitor_not_found',
            'cid': get_current_cid()
        }, status_code = 404)
    
    return monitor

def add_monitor(payload, db):
    try: 
        if payload.type == 'tcp' and not_match_tcp_url_format(payload.url):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Invalid TCP URL format',
                'i18n_code': 'invalid_tcp_url_format',
                'cid': get_current_cid()
            }, status_code = 400)
        
        if payload.type == 'http' and is_not_http_status_code(payload.expected_http_code):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Invalid HTTP status code',
                'i18n_code': 'invalid_http_status_code',
                'cid': get_current_cid()
            }, status_code = 400)
        
        new_monitor = Monitor(**payload.dict())
        hash, hashed_monitor_name = generate_hashed_name(new_monitor.name)
        new_monitor.name = hashed_monitor_name
        new_monitor.hash = hash
        current_date = datetime.now().date().strftime('%Y-%m-%d')
        new_monitor.created_at = current_date
        new_monitor.updated_at = current_date
        new_monitor.save(db)

        return JSONResponse(content = {
            'status': 'ok',
            'message': 'Monitor successfully created',
            'id': str(new_monitor.id),
            'i18n_code': 'monitor_created'
        }, status_code = 201)

    except HTTPException as e:
        return JSONResponse(content = {
            'status': 'ko',
            'message': e.detail,
            'cid': get_current_cid()
        }, status_code = e.status_code)

def update_monitor(monitor_id, payload, db):
    monitor = Monitor.findMonitorById(monitor_id, db)
    if not monitor:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Monitor not found',
            'i18n_code': 'monitor_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    if payload.type == 'tcp' and not_match_tcp_url_format(payload.url):
            return JSONResponse(content = {
                'status': 'ko',
                'error': 'Invalid TCP URL format',
                'i18n_code': 'invalid_tcp_url_format',
                'cid': get_current_cid()
            }, status_code = 400)

    if payload.type == 'http' and is_not_http_status_code(payload.expected_http_code):
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Invalid HTTP status code',
            'i18n_code': 'invalid_http_status_code',
            'cid': get_current_cid()
        }, status_code = 400)

    # ? temporary procedure for old monitors with null hash
    if is_empty(monitor.hash):
        _, hash = monitor.name.rsplit('-', 1)
        monitor.hash = hash

    payload.name = "{}-{}".format(payload.name, monitor.hash)
    Monitor.adminUpdateInfo(payload, monitor_id, db)

    return JSONResponse(content = {
        'status': 'ok',
        'message': 'Monitor successfully updated',
        'id': monitor_id,
        'i18n_code': 'monitor_updated'
    })

def remove_monitor(monitor_id, db):
    monitor = Monitor.findMonitorById(monitor_id, db)
    if not monitor:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Monitor not found',
            'i18n_code': 'monitor_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    Monitor.deleteMonitor(monitor_id, db)

    return JSONResponse(content = {
        'status': 'ok',
        'message': 'Monitor successfully deleted',
        'id': monitor_id,
        'i18n_code': 'monitor_deleted'
    })
