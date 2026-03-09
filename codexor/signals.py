"""Signal extraction from Codex output."""

from __future__ import annotations

import re

from .models import FinalSignal

ANSI_ESCAPE_PATTERN = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def normalize_terminal_text(value: str) -> str:
    """Remove common ANSI escape sequences and trim whitespace."""
    stripped = ANSI_ESCAPE_PATTERN.sub("", value)
    return stripped.strip()


def parse_final_signal(output_tail: str) -> FinalSignal:
    """Search for the final handshake signal in the output tail."""
    normalized = normalize_terminal_text(output_tail)
    
    if re.search(r"\bALL DONE\b", normalized, flags=re.IGNORECASE):
        return FinalSignal.ALL_DONE
    if re.search(r"\bBREAK ON ERROR\b", normalized, flags=re.IGNORECASE):
        return FinalSignal.BREAK_ON_ERROR
        
    return FinalSignal.INVALID


def parse_summary(output_tail: str) -> str:
    """Parse the final summary from the output tail, if present."""
    normalized = normalize_terminal_text(output_tail)
    # Search for the last occurrence of summary tags
    matches = list(re.finditer(r"<summary>(.*?)</summary>", normalized, flags=re.DOTALL | re.IGNORECASE))
    if matches:
        return matches[-1].group(1).strip()
    return ""
