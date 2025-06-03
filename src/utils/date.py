import re
import time

from datetime import datetime
from utils.common import is_empty, is_false, is_not_empty, is_true
from utils.logger import log_msg

_simple_date_format = "%Y-%m-%d"
_date_hour_format_iso = "{}T%H:%M:%S".format(_simple_date_format)
_date_hour_format_space = "{} %H:%M:%S".format(_simple_date_format)
_date_hour_format_timezone = "{}.%fZ".format(_date_hour_format_iso)

def parse_date(vdate, last_hour = False):
    log_msg("DEBUG", "[parse_date] trying to parse {}".format(vdate))
    if is_empty(vdate):
        return {
            'status': False,
            'value': None
        }

    if isinstance(vdate, dict):
        return vdate if 'status' in vdate and 'value' in vdate else {
            'status': False,
            'value': vdate
        }

    if isinstance(vdate, datetime):
        return {
            'status': True,
            'value': vdate
        }

    fdate = vdate.replace('/', '-')

    try:
        parsed_date = datetime.strptime(fdate, _date_hour_format_timezone)
    except ValueError:
        try:
            parsed_date = datetime.strptime(fdate, _date_hour_format_iso)
        except ValueError:
            try:
                parsed_date = datetime.strptime(fdate, _date_hour_format_space)
            except ValueError:
                try:
                    if is_true(last_hour):
                        parsed_date = datetime.strptime(f"{fdate}T23:59:59", _date_hour_format_iso)
                    else:
                        parsed_date = datetime.strptime(fdate, _simple_date_format)
                except ValueError:
                    parsed_date = None

    if is_not_empty(parsed_date):
        return {
            'status': True,
            'value': parsed_date
        }
    else:
        return {
            'status': False,
            'value': fdate
        }

def is_iso_date_valid(date):
    pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\+\d{2}:\d{2})?$'
    return bool(re.match(pattern, date))

def is_after(date_before, date_after):
    parsed_before = parse_date(date_before)
    parsed_after = parse_date(date_after)

    if is_false(parsed_before['status']) or is_false(parsed_after['status']):
        return False
    
    return parsed_after['value'] >= parsed_before['value']

def is_after_current_time(date):
    return is_after(time.strftime(_date_hour_format_iso, time.gmtime()), date)
