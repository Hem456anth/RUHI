class ToolError(RuntimeError):
    """Raised by a shared tool when it cannot complete its work.

    Carries a human-readable ``message`` and an optional structured ``code``
    so agents can decide whether to retry, fall back, or surface to the user.
    """

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code
