"""Codex process runner with interactive passthrough and output tail capture."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import threading
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

from .models import CodexRunResult

DEFAULT_CODEX_COMMAND = ["codex", "--yolo", "--no-alt-screen"]


@dataclass(slots=True)
class _OutputTailTracker:
    """Tracks the most recent non-empty line from streamed terminal output."""

    max_tail_chars: int = 20_000
    _current_line: str = field(default="", init=False)
    _last_non_empty: str = field(default="", init=False)
    _tail_text: str = field(default="", init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self) -> None:
        pass

    def feed(self, text: str) -> None:
        with self._lock:
            self._tail_text = (self._tail_text + text)[-self.max_tail_chars :]
            for char in text:
                if char in ("\n", "\r"):
                    stripped = self._current_line.strip()
                    if stripped:
                        self._last_non_empty = stripped
                    self._current_line = ""
                else:
                    self._current_line += char

    def finalize(self) -> None:
        with self._lock:
            stripped = self._current_line.strip()
            if stripped:
                self._last_non_empty = stripped
            self._current_line = ""

    @property
    def last_non_empty(self) -> str:
        with self._lock:
            return self._last_non_empty

    @property
    def tail_text(self) -> str:
        with self._lock:
            return self._tail_text


def _resolve_codex_command(cli_tool: str = "codex") -> list[str]:
    """Resolve command, allowing environment override for testing."""
    override = os.environ.get("CODEXOR_CODEX_CMD", "").strip()
    if override:
        if os.name == "nt":
            return shlex.split(override, posix=False)
        return shlex.split(override, posix=True)
        
    if cli_tool == "gemini":
        return ["gemini", "--yolo"]
    elif cli_tool == "claude":
        return ["claude", "yolo"]
    
    # default to codex
    return ["codex", "--dangerously-bypass-approvals-and-sandbox", "--no-alt-screen"]


class CodexRunner:
    """Runs codex process and streams IO in real time."""

    def __init__(self, command: list[str] | None = None, cli_tool: str = "codex") -> None:
        self.cli_tool = cli_tool
        self.command = command if command is not None else _resolve_codex_command(cli_tool)

    def run(self, prompt: str, cwd: Path) -> CodexRunResult:
        tracker = _OutputTailTracker()
        
        import shutil
        import tempfile
        
        # Resolve executable to handle Windows .bat/.cmd files properly
        executable = self.command[0]
        resolved_executable = shutil.which(executable)
        
        # We'll handle prompt passing via shell variables/files to ensure multi-line works
        with tempfile.TemporaryDirectory(prefix="codexor-") as tmpdir:
            log_file = Path(tmpdir) / "output.log"
            prompt_file = Path(tmpdir) / "prompt.txt"
            prompt_file.write_text(prompt, encoding="utf-8")
            
            if sys.platform == "win32":
                # Create a wrapper PS1 to use Start-Transcript and pass prompt via variable
                wrapper_ps1 = Path(tmpdir) / "run.ps1"
                
                # Build the argument string for the inner command
                inner_args = []
                for arg in self.command[1:]:
                    # Double up quotes for PowerShell string literals
                    inner_args.append('"' + arg.replace('"', '""') + '"')
                
                ps_content = [
                    # Use -Raw to ensure newlines are preserved exactly
                    f'$p_text = Get-Content -Path "{prompt_file}" -Raw',
                    f'Start-Transcript -Path "{log_file}" -Append -Force',
                    f'& "{resolved_executable}" {" ".join(inner_args)} $p_text',
                    '$exit = $LASTEXITCODE',
                    'Stop-Transcript',
                    'exit $exit'
                ]
                wrapper_ps1.write_text("\n".join(ps_content), encoding="utf-8")
                
                cmd_to_run = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(wrapper_ps1)]
            else:
                # Use script on Unix
                import shlex
                flat_cmd = shlex.join(self.command + [prompt])
                if sys.platform == "darwin":
                    cmd_to_run = ["script", "-q", str(log_file), flat_cmd]
                else:
                    cmd_to_run = ["script", "-q", "-e", "-c", flat_cmd, str(log_file)]

            # stdout=None and stderr=None means it inherits the parent terminal's handles
            # This allows the child to pass TTY checks and remain interactive
            process = subprocess.Popen(
                cmd_to_run,
                cwd=str(cwd),
                stdin=sys.stdin, 
                stdout=None,
                stderr=None,
            )

            try:
                exit_code = process.wait()
            except KeyboardInterrupt:
                try:
                    if sys.platform != "win32":
                        import signal
                        process.send_signal(signal.SIGINT)
                except Exception:
                    pass
                
                try:
                    exit_code = process.wait(timeout=10.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    exit_code = process.wait()
                raise
            
            # Read log file and feed tracker
            if log_file.exists():
                import time
                time.sleep(0.5) # Give OS time to flush
                # Transcript might have BOM or different encoding
                text = log_file.read_text(encoding="utf-8-sig", errors="replace")
                tracker.feed(text)
                tracker.finalize()

        return CodexRunResult(
            exit_code=exit_code,
            last_non_empty_line=tracker.last_non_empty,
            output_tail=tracker.tail_text,
        )
