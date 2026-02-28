"""Domain errors for codexor."""


class CodexorError(Exception):
    """Base error for codexor failures."""


class ValidationError(CodexorError):
    """Raised when user input or configuration is invalid."""


class ExternalCommandError(CodexorError):
    """Raised when an external command exits with a non-zero status."""

    def __init__(self, command: list[str], exit_code: int, stderr: str) -> None:
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr
        rendered = " ".join(command)
        message = f"Command failed ({exit_code}): {rendered}"
        if stderr.strip():
            message = f"{message}\n{stderr.strip()}"
        super().__init__(message)


class DirtyWorktreeError(CodexorError):
    """Raised when local repo has uncommitted changes."""
