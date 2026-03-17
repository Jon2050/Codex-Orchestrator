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
    
    # Use 'exec' mode for codex to avoid TTY requirements while remaining interactive
    # The '-' argument tells codex to read the prompt from stdin.
    return ["codex", "exec", "--full-auto", "-"]


class CodexRunner:
    """Runs codex process and streams IO in real time."""

    def __init__(self, command: list[str] | None = None, cli_tool: str = "codex") -> None:
        self.cli_tool = cli_tool
        self.command = command if command is not None else _resolve_codex_command(cli_tool)

    def run(self, prompt: str, cwd: Path) -> CodexRunResult:
        import tempfile
        import os
        import codecs

        fd, prompt_path = tempfile.mkstemp(suffix=".md", prefix="codexor_prompt_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(prompt.rstrip() + "\n")
        
        import shutil
        
        # Resolve executable to handle Windows .bat/.cmd files properly
        executable = self.command[0]
        resolved_executable = shutil.which(executable)
        cmd_to_run = [resolved_executable] + self.command[1:] if resolved_executable else self.command.copy()
        
        if "-" in cmd_to_run:
            # Replace the standalone '-' with the file path
            idx = cmd_to_run.index("-")
            cmd_to_run[idx] = prompt_path
        else:
            cmd_to_run.append(prompt_path)
            
        process = subprocess.Popen(
            cmd_to_run,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )

        assert process.stdout is not None
        assert process.stdin is not None

        stop_event = threading.Event()

        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

        def forward_output() -> None:
            while True:
                try:
                    chunk = process.stdout.read(1024)
                    if not chunk:
                        break
                    
                    text = decoder.decode(chunk)
                    
                    # Prevent single \r from trashing previous output lines by enforcing vertical scrolling
                    display_text = text.replace("\r\n", "\n").replace("\r", "\n")
                    sys.stdout.write(display_text)
                    sys.stdout.flush()
                    
                    tracker.feed(text)
                except Exception:
                    break

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
            try:
                process.stdin.close()
            except Exception:
                pass
            try:
                process.stdout.close()
            except Exception:
                pass
            
            # Clean up the temporary prompt file
            try:
                os.remove(prompt_path)
            except OSError:
                pass

        output_thread.join(timeout=1)
        return CodexRunResult(
            exit_code=exit_code,
            last_non_empty_line=tracker.last_non_empty,
            output_tail=tracker.tail_text,
        )
