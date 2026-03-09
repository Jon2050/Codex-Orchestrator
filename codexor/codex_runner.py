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
        return ["gemini", "run"] # Gemini CLI command for non-interactive task runner
    elif cli_tool == "claude":
        return ["claude", "yolo"] # Example Claude command (placeholder if real one differs)
    
    # default to codex
    return ["codex", "--yolo", "--no-alt-screen"]


class CodexRunner:
    """Runs codex process and streams IO in real time."""

    def __init__(self, command: list[str] | None = None, cli_tool: str = "codex") -> None:
        self.command = command if command is not None else _resolve_codex_command(cli_tool)

    def run(self, prompt: str, cwd: Path) -> CodexRunResult:
        tracker = _OutputTailTracker()
        process = subprocess.Popen(
            self.command,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )

        assert process.stdout is not None
        assert process.stdin is not None

        stop_event = threading.Event()

        def forward_output() -> None:
            while True:
                chunk = process.stdout.read(1024)
                if not chunk:
                    break
                text = chunk.decode(errors="replace")
                sys.stdout.write(text)
                sys.stdout.flush()
                tracker.feed(text)

        def forward_input() -> None:
            while not stop_event.is_set():
                try:
                    if sys.platform == "win32":
                        import msvcrt
                        import time
                        if not msvcrt.kbhit():
                            time.sleep(0.1)
                            continue
                    else:
                        import select
                        r, _, _ = select.select([sys.stdin], [], [], 0.1)
                        if not r:
                            continue
                            
                    line = sys.stdin.buffer.readline()
                    if not line:
                        break
                    if stop_event.is_set() or process.poll() is not None:
                        break
                    process.stdin.write(line)
                    process.stdin.flush()
                except OSError:
                    break
                except ValueError:
                    break
                except Exception:
                    break

        output_thread = threading.Thread(target=forward_output, daemon=True)
        input_thread = threading.Thread(target=forward_input, daemon=True)
        output_thread.start()

        # Send issue-specific prompt first, then keep interactive passthrough active.
        process.stdin.write((prompt.rstrip() + "\n").encode())
        process.stdin.flush()
        input_thread.start()

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
        finally:
            stop_event.set()
            tracker.finalize()
            if process.stdin:
                process.stdin.close()
            if process.stdout:
                process.stdout.close()

        output_thread.join(timeout=1)
        return CodexRunResult(
            exit_code=exit_code,
            last_non_empty_line=tracker.last_non_empty,
            output_tail=tracker.tail_text,
        )
