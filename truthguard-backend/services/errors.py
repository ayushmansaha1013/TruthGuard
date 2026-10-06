"""
errors.py — One shared exception type for all "expected" service failures.

WHY:
    When Hugging Face is down, a key is missing, or an image is invalid, we
    don't want the app to crash with an ugly 500 stack trace. Instead, services
    raise `ServiceError`, and main.py converts it into a clean JSON response
    with a sensible HTTP status code:

        {"detail": "human readable message", "error_code": "machine_readable_tag"}

    Your frontend teammate can show `detail` to the user directly.
"""


class ServiceError(Exception):
    """An expected, user-facing failure raised by any TruthGuard service."""

    def __init__(self, status_code: int, detail: str, error_code: str = "service_error"):
        self.status_code = status_code   # HTTP status to return (400, 413, 429, 502, 503, 504...)
        self.detail = detail             # message safe to show to end users
        self.error_code = error_code     # short snake_case tag for programmatic handling
        super().__init__(detail)
