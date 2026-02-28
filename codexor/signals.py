"""Signal extraction from Codex output."""

from __future__ import annotations

import re

from .models import FinalSignal

ANSI_ESCAPE_PATTERN = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def normalize_terminal_text(value: str) -> str:
    """Remove common ANSI escape sequences and trim whitespace."""
    stripped = ANSI_ESCAPE_PATTERN.sub("", value)
    return stripped.strip()


def parse_final_signal(last_non_empty_line: str) -> FinalSignal:
    """Parse the final handshake signal from the last non-empty line."""
    normalized = normalize_terminal_text(last_non_empty_line)
    if normalized == FinalSignal.ALL_DONE.value:
        return FinalSignal.ALL_DONE
    if normalized == FinalSignal.BREAK_ON_ERROR.value:
        return FinalSignal.BREAK_ON_ERROR
    return FinalSignal.INVALID
