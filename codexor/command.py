"""External command helpers."""

from __future__ import annotations

import subprocess
import shutil
from pathlib import Path

from .errors import ExternalCommandError


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = True,
) -> str:
    """Run a command and return stdout or raise a domain-specific exception."""
    executable = command[0]
    resolved_executable = shutil.which(executable)
    
    if resolved_executable:
        command[0] = resolved_executable
        
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=capture_output,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ExternalCommandError(command, completed.returncode, completed.stderr or "")
    return completed.stdout or ""
