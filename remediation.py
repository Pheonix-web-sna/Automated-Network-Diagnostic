"""Safe, explicitly confirmed remediation actions for Windows networking."""

from dataclasses import dataclass
from datetime import datetime
import subprocess
from typing import Callable, Optional, Sequence
import config as cfg


ACTION_LABELS = {
    "flush_dns": "Flush DNS cache",
    "renew_ip": "Renew IP address",
    "rerun_diagnostics": "Re-run diagnostics",
}

CONFIRMATION_REQUIRED_ACTIONS = frozenset({"flush_dns", "renew_ip"})

_COMMANDS = {
    "flush_dns": ("ipconfig", "/flushdns"),
    "renew_ip": ("ipconfig", "/renew"),
}


@dataclass(frozen=True)
class RemediationOutcome:
    action: str
    status: str
    message: str
    timestamp: datetime

    @property
    def succeeded(self) -> bool:
        return self.status == "completed"


@dataclass(frozen=True)
class ActionRecord:
    action: str
    status: str
    details: str
    timestamp: datetime


def execute_remediation(
    action: str,
    *,
    confirmed: bool = False,
    diagnostic_callback: Optional[Callable[[], None]] = None,
    command_runner: Optional[Callable[..., object]] = None,
) -> RemediationOutcome:
    """Run one allow-listed action; network-changing actions require confirmation.

    Commands are passed as argument lists with shell disabled. Unknown actions are
    rejected, and command failures are returned as outcomes for the UI to report.
    """
    if action not in ACTION_LABELS:
        raise ValueError(f"Unsupported remediation action: {action}")

    if action == "rerun_diagnostics":
        if diagnostic_callback is None:
            return RemediationOutcome(
                action, "failed", "Diagnostic callback is unavailable.", datetime.now()
            )
        try:
            started = diagnostic_callback()
        except Exception as exc:
            return RemediationOutcome(
                action, "failed", f"Could not start diagnostics: {exc}", datetime.now()
            )
        if started is False:
            return RemediationOutcome(
                action, "failed", "A diagnostic scan is already running.", datetime.now()
            )
        return RemediationOutcome(
            action, "completed", "Diagnostic scan started.", datetime.now()
        )

    if action in CONFIRMATION_REQUIRED_ACTIONS and not confirmed:
        return RemediationOutcome(
            action, "cancelled", "User confirmation was not provided.", datetime.now()
        )

    if action not in _COMMANDS:
        raise ValueError(f"No command is defined for remediation action: {action}")

    runner = command_runner or subprocess.run
    command: Sequence[str] = _COMMANDS[action]
    try:
        completed = runner(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=cfg.REMEDIATION_COMMAND_TIMEOUT_SEC,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        return RemediationOutcome(
            action, "failed", f"Command could not be run: {exc}", datetime.now()
        )

    stdout = (getattr(completed, "stdout", "") or "").strip()
    stderr = (getattr(completed, "stderr", "") or "").strip()
    return_code = getattr(completed, "returncode", 1)
    message = stdout or stderr or (
        f"{ACTION_LABELS[action]} {'completed successfully' if return_code == 0 else 'failed'}."
    )
    return RemediationOutcome(
        action,
        "completed" if return_code == 0 else "failed",
        message,
        datetime.now(),
    )
