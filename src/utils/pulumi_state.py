"""Pulumi deprecated the legacy DIY (filestate) layout: stacks created with it fail
with "Legacy DIY state is deprecated, please upgrade your state to project mode".
We run `pulumi state upgrade` through the automation SDK, in quiet mode: a failure
is only logged as a WARN (log_msg, so it's also notified on Discord/Slack), it never
stops the process.

The upgrade runs at startup and, until it has succeeded once, again right before
any stack operation (instances, buckets, registries, DNS records...), at most every
PULUMI_STATE_UPGRADE_RETRY seconds: every driver goes through the create_stack /
select_stack / create_or_select_stack wrappers below instead of calling
pulumi.automation directly."""

import os
import time
from threading import Lock, Thread

from pulumi import automation as auto

from utils.common import get_env_int
from utils.logger import log_msg

_UPGRADE_ARGS = ["state", "upgrade", "--yes", "--non-interactive"]
_RETRY_SECONDS = get_env_int("PULUMI_STATE_UPGRADE_RETRY", 600)

PULUMI_ENV = {
    'PULUMI_DIY_BACKEND_IGNORE_DEPRECATION_ERROR': '1',
    'PULUMI_DIY_BACKEND_NO_LEGACY_WARNING': '1',
}

# Stack operations spawn the pulumi CLI with the process environment.
for _k, _v in PULUMI_ENV.items():
    os.environ.setdefault(_k, _v)

_lock = Lock()
_upgraded = False
_last_attempt = None


def upgrade_pulumi_state(force = True):
    global _upgraded, _last_attempt
    with _lock:
        if _upgraded or (not force and _last_attempt is not None and time.monotonic() - _last_attempt < _RETRY_SECONDS):
            return _upgraded
        _last_attempt = time.monotonic()
        try:
            result = auto.PulumiCommand().run(_UPGRADE_ARGS, os.getcwd(), dict(PULUMI_ENV))
            _upgraded = True
            log_msg("INFO", "[pulumi_state] state upgraded: {}".format((result.stdout or "").strip() or "nothing to do"))
        except Exception as e:
            log_msg("WARN", "[pulumi_state] pulumi state upgrade failed (ignored): {}".format(e))
        return _upgraded


def start_pulumi_state_upgrade():
    """Non-blocking: the upgrade runs in a daemon thread so startup isn't delayed."""
    Thread(target = upgrade_pulumi_state, name = "pulumi-state-upgrade", daemon = True).start()


def _run(op, *args, **kwargs):
    upgrade_pulumi_state(force = False)
    try:
        return op(*args, **kwargs)
    except auto.StackAlreadyExistsError:
        raise
    except Exception as e:
        stack = kwargs.get('stack_name', args[0] if args else None)
        project = kwargs.get('project_name', args[1] if len(args) > 1 else None)
        log_msg("WARN", "[pulumi_state] {} failed: stack = {}, project = {}, e.type = {}, e.msg = {}".format(op.__name__, stack, project, type(e).__name__, e))
        raise


def create_stack(*args, **kwargs):
    return _run(auto.create_stack, *args, **kwargs)


def select_stack(*args, **kwargs):
    return _run(auto.select_stack, *args, **kwargs)


def create_or_select_stack(*args, **kwargs):
    return _run(auto.create_or_select_stack, *args, **kwargs)
