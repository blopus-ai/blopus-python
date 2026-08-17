"""Typed exception hierarchy for the Blopus SDK.

Every error the API returns has the shape ``{"error": {"code": ..., "message": ...}}``.
:func:`error_from_response` maps that (plus the HTTP status) onto one of the
concrete exception classes below so callers can ``except blopus.QuotaError`` etc.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class BlopusError(Exception):
    """Base class for every error raised by this SDK.

    Attributes:
        message: Human-readable message (from the API when available).
        code: Machine-readable error code from the API (e.g. ``"quota_exceeded"``).
        status: HTTP status code, when the error came from an HTTP response.
        retry_after: Seconds to wait before retrying, parsed from ``Retry-After``.
        response: The parsed JSON body of the error response, if any.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        status: Optional[int] = None,
        retry_after: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.retry_after = retry_after
        self.response = response

    def __str__(self) -> str:  # pragma: no cover - trivial
        parts = [self.message]
        if self.code:
            parts.append(f"(code={self.code})")
        if self.status is not None:
            parts.append(f"[HTTP {self.status}]")
        return " ".join(parts)


class APIConnectionError(BlopusError):
    """The request never got an HTTP response (DNS, TCP, TLS, timeout)."""


class AuthError(BlopusError):
    """Missing / invalid / revoked API key, or key not permitted (401 / 403)."""


class BadRequestError(BlopusError):
    """The request was malformed or too large (400 / 413)."""


class NotFoundError(BlopusError):
    """No indexed content for the requested URL (404 from /v1/fetch)."""


class RateLimitError(BlopusError):
    """Token-bucket rate limit exceeded (429). See ``retry_after``."""


class QuotaError(BlopusError):
    """Monthly plan quota exhausted (402). Upgrade the plan or wait for reset."""


class ServerError(BlopusError):
    """The gateway or its backend failed (>= 500, incl. 503 upstream_unavailable)."""


# code -> exception class (authoritative when the body carries an error code)
_CODE_MAP = {
    "unauthorized": AuthError,
    "forbidden": AuthError,
    "bad_request": BadRequestError,
    "payload_too_large": BadRequestError,
    "not_found": NotFoundError,
    "rate_limited": RateLimitError,
    "quota_exceeded": QuotaError,
    "upstream_unavailable": ServerError,
    "internal_error": ServerError,
}


def _class_for_status(status: int) -> type[BlopusError]:
    if status in (401, 403):
        return AuthError
    if status == 402:
        return QuotaError
    if status == 404:
        return NotFoundError
    if status == 429:
        return RateLimitError
    if status in (400, 413, 422):
        return BadRequestError
    if status >= 500:
        return ServerError
    return BlopusError


def error_from_response(
    status: int,
    body: Optional[Dict[str, Any]],
    retry_after: Optional[int] = None,
) -> BlopusError:
    """Build the right exception from an HTTP status + parsed JSON body."""
    code = None
    message = None
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            code = err.get("code")
            message = err.get("message")
        elif isinstance(err, str):
            message = err
    cls = _CODE_MAP.get(code or "", None) or _class_for_status(status)
    if not message:
        message = f"Blopus API error (HTTP {status})"
    return cls(
        message,
        code=code,
        status=status,
        retry_after=retry_after,
        response=body,
    )
