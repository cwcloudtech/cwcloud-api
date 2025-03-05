import shlex
from subprocess import check_output, PIPE, CalledProcessError # nosec B404
from utils.common import is_empty
from utils.logger import log_msg

def get_script_output(cmd):
    log_msg("DEBUG", f"[get_script_output] cmd = {cmd}")
    try:
        cmd_args = shlex.split(cmd)
        return True, check_output(cmd_args, stderr=PIPE, universal_newlines=True) # nosec B603
    except CalledProcessError as e:
        stderr = f"{e.stderr}"
        if is_empty(stderr):
            stderr = str(e)
        log_msg("ERROR", f"Command cmd={cmd} is failing with error: {stderr}")
        return False, e.stderr
