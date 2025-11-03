from schemas.faas.InvocationContent import InvocationContent
from schemas.faas.InvocationArg import InvocationArgument
from schemas.faas.Invocation import Invocation

from utils.common import is_not_empty
from utils.logger import log_msg

_in_progress = "in_progress"
_states = ["complete", _in_progress, "error"]

def is_known_state(state):
    return is_not_empty(state) and any(c == "{}".format(state).lower() for c in _states)

def is_unknown_state(state):
    return not is_known_state(state)

def convert_to_invocation(function_id, body, key):
    log_msg("DEBUG", f"[convert_to_invocation] creating invocation with body = {body} with key = {key}")
    arg = InvocationArgument(
        key = key,
        value = body
    )

    content = InvocationContent(
        function_id = function_id,
        args = [arg]
    )

    return Invocation(
        content = content
    )
