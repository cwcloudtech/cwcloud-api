import os
import re
import asyncio
import socket
import threading
import time
import requests

from datetime import datetime
from time import sleep

from requests.auth import HTTPBasicAuth

from utils.common import del_key_if_exists, get_env_int, get_or_else, is_empty_key, is_not_empty, is_not_empty_key, is_true, sanitize_header_name, sanitize_metric_name
from utils.faas.iot import send_payload_in_realtime
from utils.http import HTTP_REQUEST_TIMEOUT
from utils.logger import LOG_LEVEL, get_int_value_level, log_msg
from utils.observability.enums import Method
from utils.observability.gauge import create_gauge, set_gauge
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.env_vars import APP_ENV, APP_VERSION, DOMAIN

MONITOR_SRC = os.getenv("MONITOR_SRC", "cwcloud-api")
MONITOR_WAIT_TIME = get_env_int("MONITOR_WAIT_TIME", 300)
_supported_monitor_types = ["http", "tcp"]

imalive_gauges = {}

def convert_imalive_metric_to_gauge(name, node, payload, key, labels):
    if is_not_empty_key(payload, key):
        disk = payload[key]
        for k in ['total', 'used', 'free', 'percent']:
            metric_name = f"imalive_{name}_{k}"
            if metric_name not in imalive_gauges:
                imalive_gauges[metric_name] = create_gauge(metric_name, f"imalive {name} {k}", list(labels.keys()))
            set_gauge(imalive_gauges[metric_name], disk.get(k, 0), labels)

def ingest_imalive_payload(payload, user_id):
    node_name = get_or_else(payload, 'name', 'unknown')
    pmonitor = get_or_else(payload, 'monitor', {})
    monitor_name = get_or_else(pmonitor, 'name', 'unknown')
    gauge_key = sanitize_metric_name(monitor_name)
    labels = ['name', 'family', 'kind', 'env', 'source', 'url', 'version', 'user', 'node']

    base_metric_labels = {
        'name': gauge_key,
        'family': get_or_else(pmonitor, 'family', gauge_key),
        'source': MONITOR_SRC,
        'url': DOMAIN,
        'env': APP_ENV,
        'version': APP_VERSION,
        'user': str(user_id),
        'node': node_name,
    }

    if is_not_empty_key(payload, 'monitor'):
        if gauge_key not in imalive_gauges:
            imalive_gauges[gauge_key] = {
                'result': create_gauge(f"imalive_{gauge_key}_result", f"imalive {gauge_key} result", labels),
                'duration': create_gauge(f"imalive_{gauge_key}_duration", f"imalive {gauge_key} duration", labels)
            }
        value = 1 if get_or_else(payload, 'status', 'ko') == 'ok' else 0
        duration = get_or_else(payload, 'duration', 0)
        set_gauge(imalive_gauges[gauge_key]['result'], value, {**base_metric_labels, 'kind': 'result'})
        set_gauge(imalive_gauges[gauge_key]['duration'], duration, {**base_metric_labels, 'kind': 'duration'})

    convert_imalive_metric_to_gauge('disk', node_name, payload, 'disk_usage', base_metric_labels)
    convert_imalive_metric_to_gauge('ram', node_name, payload, 'virtual_memory', base_metric_labels)
    convert_imalive_metric_to_gauge('swap', node_name, payload, 'swap_memory', base_metric_labels)

    if is_not_empty_key(payload, 'cpu'):
        cpu = payload['cpu']
        if is_not_empty_key(cpu, 'percent') and is_not_empty_key(cpu['percent'], 'all'):
            metric_name = f"imalive_cpu_all"
            if metric_name not in imalive_gauges:
                imalive_gauges[metric_name] = create_gauge(metric_name, "imalive cpu percent all", list(base_metric_labels.keys()))
            set_gauge(imalive_gauges[metric_name], cpu['percent']['all'], base_metric_labels)

def check_status_code_pattern(actual_code, pattern):
    regexp = "^{}$".format(pattern.replace('*', '[0-9]+'))
    return bool(re.match(regexp, str(actual_code)))

def match_tcp_url_format(url):
    return re.match(r"^[a-zA-Z0-9.-]+:\d+$", url)

def not_match_tcp_url_format(url):
    return not match_tcp_url_format(url)

async def async_send_payload_in_realtime(callback, safe_payload):
    await send_payload_in_realtime(callback, safe_payload)

def get_level_monitor(monitor):
    level = get_or_else(monitor, 'level', 'DEBUG')
    if level not in ['INFO', 'DEBUG']:
        level = 'DEBUG'

    return level

def process_callbacks(monitor, payload):
    if is_empty_key(monitor, 'callbacks'):
        return

    if get_int_value_level(get_level_monitor(monitor)) < get_int_value_level(LOG_LEVEL) and is_true(payload['status']):
        return

    try:
        for callback in monitor["callbacks"]:
            if is_empty_key(callback, "endpoint"):
                continue

            if callback["type"] == "http":
                callback_headers = ({
                    "Authorization": callback["token"],
                    "Content-Type": "application/json",
                } if is_not_empty_key(callback, "token") else {
                    "Content-Type": "application/json"
                })

                try:
                    requests.post(callback["endpoint"], json=payload, headers=callback_headers, timeout=HTTP_REQUEST_TIMEOUT)
                    log_msg("DEBUG", f"[monitor][process_callbacks] monitor result sent to: {callback['endpoint']}")
                except Exception as e:
                    log_msg("ERROR", f"Failed to send HTTP callback: e.type = {type(e)}, e.msg = {str(e)}")
            elif callback["type"] in ["websocket", "mqtt"]:
                try:
                    asyncio.run(async_send_payload_in_realtime(callback, payload))
                except Exception as e:
                    log_msg("ERROR", f"Failed to send {callback['type']} callback: e.type = {type(e)}, e.msg = {str(e)}")
    except Exception as e:
        log_msg("ERROR", f"Error processing callbacks: e.type = {type(e)}, e.msg = {str(e)}")

def init_vars_monitor(monitor):
    vdate = datetime.now()
    timeout = get_or_else(monitor, 'timeout', 30)
    pmonitor = monitor.copy()

    if monitor['type'] == 'tcp':
        del_key_if_exists(pmonitor, 'expected_http_code')

    del_key_if_exists(pmonitor, 'username')
    del_key_if_exists(pmonitor, 'password')
    level = get_level_monitor(monitor)

    labels = {
        'name': monitor['name'],
        'family': monitor['family'] if is_not_empty_key(monitor, 'family') else monitor['name'],
        'source': MONITOR_SRC,
        'url': DOMAIN,
        'env': APP_ENV,
        'version': APP_VERSION
    }

    return vdate, labels, pmonitor, level, timeout

def check_tcp_monitor(monitor, gauges):
    vdate, labels, pmonitor, level, timeout = init_vars_monitor(monitor)
    callback_payload = {}
    duration = 0

    if not_match_tcp_url_format(monitor['url']):
        callback_payload = {
            "status": "ko",
            "type": "monitor",
            "time": vdate.isoformat(),
            "message": "Incorrect url (expected host:port): actual = {}".format(monitor['url']),
            "monitor": pmonitor
        }

        log_msg("ERROR", callback_payload)
        set_gauge(gauges['result'], 0, {**labels, 'kind': 'result', 'user': monitor['user_id']})
        set_gauge(gauges['duration'], duration, {**labels, 'kind': 'duration', 'user': monitor['user_id']})
        return duration, callback_payload

    host, port = monitor['url'].split(":")
    port = int(port)
    start_time = time.time()

    try:
        with socket.create_connection((host, port), timeout=timeout):
            duration = time.time() - start_time
            callback_payload = {
                "status": "ok",
                "type": "monitor",
                "time": vdate.isoformat(),
                "duration": duration,
                "message": "Monitor is healthy",
                "monitor": pmonitor
            }

            log_msg(level, callback_payload)
            set_gauge(gauges['result'], 1, {**labels, 'kind': 'result', 'user': monitor['user_id']})
            set_gauge(gauges['duration'], duration, {**labels, 'kind': 'duration', 'user': monitor['user_id']})
            return duration, callback_payload
            
    except (socket.timeout, ConnectionRefusedError, socket.error) as e:
        duration = time.time() - start_time
        callback_payload = {
            "status": "ko",
            "type": "monitor",
            "time": vdate.isoformat(),
            "message": "Unable to open connection, e.type = {}, e.msg = {}".format(type(e), e),
            "monitor": pmonitor
        }

        log_msg("ERROR", callback_payload)
        set_gauge(gauges['result'], 0, {**labels, 'kind': 'result', 'user': monitor['user_id']})
        set_gauge(gauges['duration'], duration, {**labels, 'kind': 'duration', 'user': monitor['user_id']})
        return duration, callback_payload

def check_http_monitor(monitor, gauges):
    vdate, labels, pmonitor, level, timeout = init_vars_monitor(monitor)
    callback_payload = {}
    method = get_or_else(monitor, 'method', 'GET')
    expected_http_code = get_or_else(monitor, 'expected_http_code', '20*')
    expected_contain = get_or_else(monitor, 'expected_contain', None)
    duration = 0
    auth = None
    headers = {}
    check_tls = is_true(get_or_else(monitor, 'check_tls', True))

    if is_not_empty_key(monitor, 'username') and is_not_empty_key(monitor, 'password'): 
        auth = HTTPBasicAuth(monitor['username'], monitor['password'])

    if is_not_empty_key(monitor, 'headers'):
        for header in monitor['headers']:
            if is_not_empty_key(header, 'name') and is_not_empty_key(header, 'value'):
                headers[sanitize_header_name(header['name'])] = header['value']

    try:
        if method == "GET":
            response = requests.get(monitor['url'], auth=auth, headers=headers, timeout=timeout, verify=check_tls)
            duration = response.elapsed.total_seconds() * 1000
        elif method == "POST":
            response = requests.post(monitor['url'], auth=auth, headers=headers, data=monitor.get('body'), timeout=timeout, verify=check_tls)
            duration = response.elapsed.total_seconds() * 1000
        elif method == "PUT":
            response = requests.put(monitor['url'], auth=auth, headers=headers, data=monitor.get('body'), timeout=timeout, verify=check_tls)
            duration = response.elapsed.total_seconds() * 1000
        else:
            callback_payload = {
                "status": "ko",
                "type": "monitor",
                "time": vdate.isoformat(),
                "message": f"Not supported http method: actual = {method}",
                "monitor": pmonitor,
            }

            log_msg("ERROR", callback_payload)
            set_gauge(gauges['result'], 0, {**labels, 'kind': 'result', 'user': monitor['user_id']})
            set_gauge(gauges['duration'], duration, {**labels, 'kind': 'duration', 'user': monitor['user_id']})
            return duration, callback_payload

        if not check_status_code_pattern(response.status_code, expected_http_code):
            callback_payload = {
                "status": "ko",
                "type": "monitor",
                "time": vdate.isoformat(),
                "duration": duration,
                "message": f"Not expected status code: expected pattern = {expected_http_code}, actual = {response.status_code}",
                "monitor": pmonitor,
            }

            log_msg("ERROR", callback_payload)
            set_gauge(gauges['result'], 0, {**labels, 'kind': 'result', 'user': monitor['user_id']})
            set_gauge(gauges['duration'], duration, {**labels, 'kind': 'duration', 'user': monitor['user_id']})
            return duration, callback_payload

        if is_not_empty(expected_contain) and expected_contain not in response.text:
            callback_payload = {
                "status": "ko",
                "type": "monitor",
                "time": vdate.isoformat(),
                "duration": duration,
                "message": f"Response not valid: expected = {expected_contain}, actual = {response.text}",
                "monitor": pmonitor,
            }

            log_msg("ERROR", callback_payload)
            set_gauge(gauges['result'], 0, {**labels, 'kind': 'result', 'user': monitor['user_id']})
            set_gauge(gauges['duration'], duration, {**labels, 'kind': 'duration', 'user': monitor['user_id']})
            return duration, callback_payload

        set_gauge(gauges['result'], 1, {**labels, 'kind': 'result', 'user': monitor['user_id']})
        set_gauge(gauges['duration'], duration, {**labels, 'kind': 'duration', 'user': monitor['user_id']})
        callback_payload = {
            "status": "ok",
            "type": "monitor",
            "time": vdate.isoformat(),
            "duration": duration,
            "message": "Monitor is healthy",
            "monitor": pmonitor,
        }

        log_msg(level, callback_payload)
        return duration, callback_payload

    except Exception as e:
        set_gauge(gauges['result'], 0, {**labels, 'kind': 'result', 'user': monitor['user_id']})
        details = {
            "type": type(e).__name__,
            "file": __file__,
            "lno": e.__traceback__.tb_lineno,
        }

        callback_payload = {
            "status": "ko",
            "type": "monitor",
            "time": vdate.isoformat(),
            "message": "Unexpected error",
            "error": f"{e}",
            "details": details,
            "monitor": pmonitor,
        }
        log_msg("ERROR", callback_payload)
        return 0, callback_payload

def check_monitor(monitor, gauges):
    callback_payload = {}
    vdate, labels, pmonitor, _, _ = init_vars_monitor(monitor)
    response_time = 0

    if monitor['type'] not in _supported_monitor_types:
        callback_payload = {
            "status": "ko",
            "type": "monitor",
            "time": vdate.isoformat(),
            "message": f"Not supported monitor type: actual = {monitor['type']}",
            "monitor": pmonitor,
        }

        log_msg("ERROR", callback_payload)
        set_gauge(gauges['result'], 0, {**labels, 'kind': 'result', 'user': monitor['user_id']})
        return response_time, callback_payload
    
    if is_empty_key(monitor, 'url'):
        callback_payload = {
            "status": "ko",
            "type": "monitor",
            "time": vdate.isoformat(),
            "message": "Missing mandatory url",
            "monitor": pmonitor,
        }

        log_msg("ERROR", callback_payload)
        set_gauge(gauges['result'], 0, {**labels, 'kind': 'result', 'user': monitor['user_id']})
        return response_time, callback_payload
    
    if monitor['type'] == 'http':
        response_time, callback_payload = check_http_monitor(monitor, gauges)
    elif monitor['type'] == 'tcp':
        response_time, callback_payload = check_tcp_monitor(monitor, gauges)

    return response_time, callback_payload

gauges = {}

def check_monitors():
    try:
        from database.postgres_db import SessionLocal
        from entities.Monitor import Monitor

        db = SessionLocal()
        loaded_data = Monitor.getAllMonitors(db)
        labels = ['name', 'family', 'kind', 'env', 'source', 'url', 'version', 'user']

        for monitor in loaded_data:
            if monitor.name not in gauges:
                gauges[monitor.name] = {
                    'result': create_gauge(f"monitor_{monitor.name}_result", f"monitor {monitor.name} result", labels),
                    'duration': create_gauge(f"monitor_{monitor.name}_duration", f"monitor {monitor.name} duration", labels)
                }

            monitor_dict = {
                "name": monitor.name,
                "family": monitor.family,
                "type": monitor.type,
                "url": monitor.url,
                "method": monitor.method,
                "timeout": monitor.timeout,
                "expected_http_code": monitor.expected_http_code,
                "body": monitor.body,
                "expected_contain": monitor.expected_contain,
                "username": monitor.username,
                "password": monitor.password,
                "user_id": monitor.user_id,
                "callbacks": monitor.callbacks if monitor.callbacks else [],
                "check_tls": monitor.check_tls,
                "level": monitor.level,
                "headers": [{"name": h["name"], "value": h["value"]} for h in monitor.headers] if monitor.headers else [],
            }

            try:
                response_time, callback_payload = check_monitor(monitor_dict, gauges[monitor.name])
                Monitor.updateMonitorStatus(monitor.id, 'success' if is_true(callback_payload['status']) else 'failure', f"{response_time} ms", db)
                process_callbacks(monitor_dict, callback_payload)
            except Exception as me:
                log_msg("ERROR", f"Error processing monitor {monitor.name}: e.type = {type(me)}, e.msg = {str(me)}")

    except Exception as e:
        details = {
            "type": type(e).__name__,
            "file": __file__,
            "lno": e.__traceback__.tb_lineno,
        }

        log_msg("ERROR", {
            "status": "ko",
            "i18n_code": "monitor_check_failed",
            "type": "monitor",
            "time": datetime.now().isoformat(),
            "message": f"Error in monitor loop: e.type = {type(e)}, e.msg = {str(e)}",
            "details": details,
        })
    finally:
        if "db" in locals():
            db.close()

def monitors():
    def loop_monitors():
        while True:
            try:
                with get_otel_tracer().start_as_current_span(span_format("monitors", Method.ASYNCWORKER)):
                    check_monitors()
            except Exception as e:
                log_msg("ERROR", f"Error in monitor loop: e.type = {type(e)}, e.msg = {str(e)}")
            finally:
                sleep(MONITOR_WAIT_TIME)

    def start_monitors():
        sleep(MONITOR_WAIT_TIME)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(loop_monitors())

    async_thread = threading.Thread(target=start_monitors, daemon=True)
    async_thread.start()
