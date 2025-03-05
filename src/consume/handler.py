import re
import requests

from jinja2 import Environment, FileSystemLoader, BaseLoader, select_autoescape

from adapters.AdapterConfig import get_adapter
from utils.command import get_script_output
from utils.common import get_env_int, get_src_path, is_not_empty, is_empty_key, is_not_empty_key, AUTOESCAPE_EXTENSIONS, is_true
from utils.faas.vars import FAAS_API_TOKEN, FAAS_API_URL
from utils.http import HTTP_REQUEST_TIMEOUT
from utils.observability.otel import get_otel_tracer
from utils.security import is_forbidden
from utils.file import quiet_remove
from utils.functions import get_ext_from_language, is_not_supported_language
from utils.logger import log_msg
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Method

_api_endpoint = "{}/v1/faas".format(FAAS_API_URL)
_functions_file_path = "/functions"
_consume_src_path = "{}/consume".format(get_src_path())
_templates_path = "{}/templates/faas/main".format(get_src_path())
_env = Environment(loader=FileSystemLoader(_templates_path), autoescape=select_autoescape(AUTOESCAPE_EXTENSIONS))

pubsub_adapter = get_adapter("pubsub")

_headers = { "X-Auth-Token": FAAS_API_TOKEN } if is_not_empty(FAAS_API_TOKEN) else None
_span_prefix = "faas-consumer"
_counter = create_counter("consumer", "consumer counter")

def update_invocation(invocation_id, payload):
  invocation_url = "{}/invocation/{}".format(_api_endpoint, invocation_id)
  log_msg("DEBUG", "[consume][update_invocation] update invocation with : {}, invocation_url = {}".format(payload, invocation_url))
  r_update_payload = requests.put(invocation_url, json=payload, headers=_headers, timeout=HTTP_REQUEST_TIMEOUT)
  if r_update_payload.status_code != 200:
    log_msg("ERROR", "[consume][update_invocation] bad response from the API: code = {}, body = {}".format(r_update_payload.status_code, r_update_payload.content))

def error_invocation(invocation_id, payload, msg):
  log_msg("ERROR", "[consumer][error_invocation] {}, payload = {}".format(msg, payload))
  payload['content']['state'] = "error"
  payload['content']['result'] = msg
  update_invocation(invocation_id, payload)

def is_user_authenticated(payload):
  log_msg("DEBUG", "[is_authenticated] serverless_function = {}".format(payload['content']['user_auth']['is_authenticated']))
  return payload['content']['user_auth']['is_authenticated']

async def handle(msg):
  with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.ASYNCWORKER)):
    increment_counter(_counter, Method.ASYNCWORKER)
    payload = pubsub_adapter().decode(msg)
    if payload is None:
      log_msg("DEBUG", "[consume][handle] payload is none")
      return

    log_msg("DEBUG", "[consume][handle] receive : {}".format(payload))
    
    if is_empty_key(payload, 'id'):
      log_msg("ERROR", "[consume][handle] the payload is not valid, missing invocation id")
      return

    invocation_id = payload['id']

    if is_empty_key(payload, 'content') or is_empty_key(payload['content'], 'function_id'):
      error_invocation(invocation_id, payload, "the invocation {} is not valid, missing function_id".format(invocation_id))
      return

    function_id = payload['content']['function_id']
    function_url = "{}/function/{}".format(_api_endpoint, function_id)
    log_msg("DEBUG", "[consume][handle] getting function_url = {}".format(function_url))
    r_serverless_function = requests.get(function_url, headers =_headers, timeout=HTTP_REQUEST_TIMEOUT)
    if r_serverless_function.status_code != 200:
      error_invocation(invocation_id, payload, "the function {} is not found".format(function_id))
      return
    
    serverless_function = r_serverless_function.json()
    if is_empty_key(serverless_function, 'content') or is_empty_key(serverless_function['content'], 'language'):
      error_invocation(invocation_id, payload, "the function {}'s definition is invalid: missing language".format(function_id))
      return

    language = serverless_function['content']['language']
    if is_not_supported_language(language):
      error_invocation(invocation_id, payload, "not supported language: {}".format(language))
      return

    if is_empty_key(serverless_function['content'], 'code'):
      error_invocation(invocation_id, payload, "the function {}'s definition is invalid: missing code".format(function_id))
      return

    if is_not_empty_key(payload['content'], 'args'):
      args = payload['content']['args']
      if any(is_forbidden(arg['value']) for arg in args):
        error_invocation(invocation_id, payload, "forbidden argument(s) for the function {}".format(function_id))
        return

      if is_not_empty_key(serverless_function['content'], 'regexp'):
          regexp = serverless_function['content']['regexp']
          if any(not re.match(regexp, arg['value']) for arg in args):
              error_invocation(invocation_id, payload, "the function {}'s definition forbid some arguments, regexp = {}".format(function_id, regexp))
              return

    try:
      payload['content']['state'] = "complete"
      ext = get_ext_from_language(language)
      function_file_path = "{}/{}.{}".format(_functions_file_path, invocation_id, ext)
      log_msg("DEBUG", "[consume][handle] write function file : {}".format(function_file_path))
      with open(function_file_path, 'w') as function_file:
        template = _env.get_template("main.{}.j2".format(ext))

        function_with_args_tpl = "handle({})"
        function_without_args_tpl = "handle()"
        args_separator = ","

        if language == "bash":
          function_with_args_tpl="handle {}"
          function_without_args_tpl="handle"
          args_separator=" "

        handle_call = function_with_args_tpl.format(args_separator.join(["\"{}\"".format(item['value']) for item in payload['content']['args']])) if is_not_empty_key(payload['content'], 'args') else function_without_args_tpl

        main_content = template.render(
          function_id=function_id,
          handle_definition=serverless_function['content']['code'],
          handle_call=handle_call
        )

        if "env" not in serverless_function['content']:
          serverless_function['content']['env'] = {}

        env = Environment(loader=BaseLoader(), autoescape=select_autoescape(AUTOESCAPE_EXTENSIONS))
        template = env.from_string(main_content)
        if is_user_authenticated(payload):
          log_msg("DEBUG", "[consume][handle] user is authenticated, user_auth_key = {}, user_auth_value = {}".format(payload['content']['user_auth']['header_key'], payload['content']['user_auth']['header_value']))
          main_content = template.render(
            user_auth_key=payload['content']['user_auth']['header_key'] ,
            user_auth_value=payload['content']['user_auth']['header_value'],
            env=serverless_function['content']['env']
          )
        else:
          main_content = template.render(
            env=serverless_function['content']['env']
          )

        function_file.write(main_content)

      status, output = get_script_output("{}/{}_eval.sh {}".format(_consume_src_path, ext, invocation_id))
      payload['content']['result'] = "{}".format(output)

      if is_true(status):
        quiet_remove(function_file_path)
      update_invocation(invocation_id, payload)
    except Exception as e:
      error_invocation(invocation_id, payload, "e.type = {}, e.msg = {}".format(type(e), e))
    finally:
      await pubsub_adapter().reply(msg, payload)
