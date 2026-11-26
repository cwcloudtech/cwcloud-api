"""Pulumi deprecated the legacy DIY (filestate) layout: stacks created with it fail
with "Legacy DIY state is deprecated, please upgrade your state to project mode".
At startup we run `pulumi state upgrade` once through the automation SDK, in quiet
mode: a failure is only logged as a WARN, it never stops the process."""

import os
from threading import Thread

from pulumi import automation as auto

from utils.logger import log_msg

_UPGRADE_ARGS = ["state", "upgrade", "--yes", "--non-interactive"]


def upgrade_pulumi_state():
    try:
        result = auto.PulumiCommand().run(_UPGRADE_ARGS, os.getcwd(), {
            'PULUMI_DIY_BACKEND_IGNORE_DEPRECATION_ERROR': '1'
        })
        log_msg("INFO", "[pulumi_state] state upgraded: {}".format((result.stdout or "").strip() or "nothing to do"))
    except Exception as e:
        log_msg("WARN", "[pulumi_state] pulumi state upgrade failed (ignored): {}".format(e))


def start_pulumi_state_upgrade():
    """Non-blocking: the upgrade runs in a daemon thread so startup isn't delayed."""
    Thread(target = upgrade_pulumi_state, name = "pulumi-state-upgrade", daemon = True).start()
