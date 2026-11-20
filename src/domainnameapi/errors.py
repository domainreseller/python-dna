"""Exceptions.

Every exception this package raises derives from :class:`DomainNameAPIError`
and has a :attr:`~DomainNameAPIError.kind`. Catch the subclass you care about::

    try:
        client.domains.renew("example.com", 1)
    except dna.InsufficientBalanceError:
        ...                                   # top up first
    except dna.NotFoundError:
        ...                                   # not in this account / environment
    except dna.DomainNameAPIError as err:
        if err.outcome_unknown:
            ...                               # it may have happened: check before retrying
        raise

Branch on :attr:`~DomainNameAPIError.code` rather than on the message: messages
are localised. The API's codes look like ``Dna.DomainService:Domain:10007``;
:class:`ErrorCode` names the common ones.
"""

from __future__ import annotations

import enum
import json
import re
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Dict, List, Mapping, Optional

__all__ = [
    "APIError",
    "AuthenticationError",
    "ConfigurationError",
    "ConflictError",
    "DecodeError",
    "DomainNameAPIError",
    "ErrorCode",
    "ErrorKind",
    "FieldError",
    "InputError",
    "InsufficientBalanceError",
    "MissingCredentialsError",
    "NetworkError",
    "NotFoundError",
    "OperationError",
    "RateLimitError",
    "ReadOnlyError",
    "RejectedError",
    "ServerError",
    "ValidationError",
    "WaitTimeoutError",
    "kind_of",
]


class ErrorKind(str, enum.Enum):
    """A coarse, stable classification of failures."""

    #: Wrong or missing credentials, the key of the other environment, or an
    #: unknown or suspended reseller (HTTP 401 or a redirect).
    AUTH = "auth"
    #: The object does not exist or is not yours (HTTP 404).
    NOT_FOUND = "not_found"
    #: The API rejected the input (HTTP 400, 422).
    VALIDATION = "validation"
    #: A business rule refused the operation (HTTP 402, 403: balance, transfer
    #: lock, TLD rules, ...), or the API answered 2xx with ``success: false``.
    REJECTED = "rejected"
    #: The object is in a conflicting state (HTTP 409).
    CONFLICT = "conflict"
    #: Still rate limited after the automatic retries (HTTP 429).
    RATE_LIMITED = "rate_limited"
    #: The API failed (HTTP 5xx); often transient.
    SERVER = "server"
    #: The request did not complete: DNS, TLS, timeout, connection reset.
    NETWORK = "network"
    #: The request's validation rejected it; nothing was sent.
    INVALID_INPUT = "invalid_input"
    #: The client is read-only and the request would change something; nothing was sent.
    READ_ONLY = "read_only"
    #: Anything else.
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return str(self.value)


class ErrorCode:
    """Error codes, for comparing with :attr:`DomainNameAPIError.code`.

    The full catalogue is at https://www.domainnameapi.com/docs/reference/errors.md.
    """

    # Codes this package sets when the API sends none.
    #: The reseller ID is unknown, inactive or suspended in this environment.
    INVALID_RESELLER = "INVALID_RESELLER"
    #: The key does not match (production and OTE keys differ).
    INVALID_API_KEY = "INVALID_API_KEY"
    #: The X-API-KEY header was empty.
    MISSING_API_KEY = "MISSING_API_KEY"
    #: The __reseller header was empty.
    MISSING_RESELLER_ID = "MISSING_RESELLER_ID"
    #: Sub-reseller accounts cannot use the API.
    SUBRESELLER_NOT_ALLOWED = "SUBRESELLER_NOT_ALLOWED"
    #: Any other 401.
    UNAUTHORIZED = "UNAUTHORIZED"
    #: 429. Otherwise the code is "HTTP_<status>", e.g. HTTP_502.
    RATE_LIMITED = "RATE_LIMITED"

    # Codes the API sends.
    #: Not found, or not yours.
    DOMAIN_NOT_FOUND = "Dna.DomainService:Domain:10007"
    #: The TLD has no WHOIS privacy.
    PRIVACY_NOT_SUPPORTED = "Dna.DomainService:Domain:10040"
    #: The domain has no URL forwarding.
    FORWARDING_NOT_FOUND = "Dna.DomainService:Domain:10061"
    #: Registered at the registry, not recorded yet.
    REGISTERED_NOT_RECORDED = "Dna.DomainService:Domain:10058"
    #: Renewed at the registry, not recorded yet.
    RENEWED_NOT_RECORDED = "Dna.DomainService:Domain:10059"
    #: Transfer started at the registry, not recorded yet.
    TRANSFER_NOT_RECORDED = "Dna.DomainService:Domain:10060"
    #: Sent to the certificate authority.
    SSL_SENT_TO_CA = "Dna.SslService:Ssl:10053"
    #: The certificate authority's answer is unknown.
    SSL_OUTCOME_UNVERIFIED = "Dna.SslService:Ssl:10054"
    #: There is no verification pending for the contact.
    VERIFICATION_NOT_PENDING = "Dna.DomainService:Contact:Verification:10005"
    #: The contact is already verified.
    VERIFICATION_ALREADY_DONE = "Dna.DomainService:Contact:Verification:10003"
    #: The balance is too low (domain operations).
    INSUFFICIENT_BALANCE = "Dna.DomainService:Deposit:10001"
    #: The balance is too low (deposit service).
    DEPOSIT_INSUFFICIENT_BALANCE = "Dna.DepositService:Deposit:10002"


#: Codes meaning "the registry or CA may already have done it": never repeat
#: the request before checking the object's state.
OUTCOME_UNKNOWN_CODES = frozenset({
    ErrorCode.REGISTERED_NOT_RECORDED,
    ErrorCode.RENEWED_NOT_RECORDED,
    ErrorCode.TRANSFER_NOT_RECORDED,
    ErrorCode.SSL_SENT_TO_CA,
    ErrorCode.SSL_OUTCOME_UNVERIFIED,
})

_INSUFFICIENT_BALANCE_CODES = frozenset({ErrorCode.INSUFFICIENT_BALANCE, ErrorCode.DEPOSIT_INSUFFICIENT_BALANCE})


@dataclass(frozen=True)
class FieldError:
    """One problem with one input field."""

    #: The field, e.g. ``"domain_name"`` or ``"contacts.Registrant.country"``.
    field: str
    #: What is wrong.
    message: str

    def __str__(self) -> str:
        return "%s: %s" % (self.field, self.message) if self.field else self.message


class DomainNameAPIError(Exception):
    """Base class of every exception of this package."""

    #: The classification of this error.
    kind: ErrorKind = ErrorKind.UNKNOWN
    #: The error code (see :class:`ErrorCode`), or ``""``.
    code: str = ""

    @property
    def outcome_unknown(self) -> bool:
        """``True`` when the failed request may still have been carried out.

        Check the object's state before sending such a request again:
        repeating a registration or renewal blindly can charge twice.
        """
        return False

    @property
    def retryable(self) -> bool:
        """``True`` when sending the same request again later may succeed."""
        return False


class ConfigurationError(DomainNameAPIError, ValueError):
    """The client was created with invalid settings (environment, base URL, ...)."""


class MissingCredentialsError(ConfigurationError):
    """The reseller ID or the API key is empty."""

    kind = ErrorKind.AUTH

    def __init__(self, message: str = ""):
        super().__init__(message or (
            "the reseller ID and the API key are required: find both in the reseller panel under "
            "API settings, or set DNA_RESELLER_ID and DNA_API_KEY"))


class InputError(DomainNameAPIError, ValueError):
    """A request's validation rejected it. Nothing was sent."""

    kind = ErrorKind.INVALID_INPUT

    def __init__(self, request: str, fields: List[FieldError]):
        self.request = request
        self.fields = list(fields)
        super().__init__("invalid %s: %s" % (request or "request", "; ".join(str(f) for f in self.fields)))


class ReadOnlyError(DomainNameAPIError):
    """The client is read-only and the request would change something. Nothing was sent."""

    kind = ErrorKind.READ_ONLY

    def __init__(self, request: str, method: str, path: str, safety: Any):
        self.request = request
        self.method = method
        self.path = path
        self.safety = safety
        super().__init__("blocked by read-only mode: %s (%s %s) is a %s request" % (
            request, method, path, safety))


class APIError(DomainNameAPIError):
    """The API answered with a non-2xx status.

    The subclasses tell the common cases apart: :class:`AuthenticationError`,
    :class:`NotFoundError`, :class:`ValidationError`, :class:`RejectedError`
    (with :class:`InsufficientBalanceError`), :class:`ConflictError`,
    :class:`RateLimitError` and :class:`ServerError`.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: str = "",
        fields: Optional[List[FieldError]] = None,
        data: Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
        retry_after: Optional[float] = None,
        method: str = "",
        path: str = "",
        body: bytes = b"",
    ):
        #: The HTTP status.
        self.status_code = status_code
        #: The API's error code, or one of the :class:`ErrorCode` codes when it sends none.
        self.code = code
        #: The API's message.
        self.message = message
        #: The API's longer explanation, when it sends one.
        self.details = details
        #: Per-field problems of a validation error.
        self.fields = list(fields or [])
        #: Extra facts some errors carry, e.g. the balances on an insufficient-balance error.
        self.data = dict(data or {})
        #: Identifies the request; quote it when contacting support.
        self.correlation_id = correlation_id
        #: Seconds the API asked to wait (429).
        self.retry_after = retry_after
        self.method = method
        self.path = path
        #: The raw response body.
        self.body = body
        super().__init__(self._describe())

    def _describe(self) -> str:
        text = "%s %s: " % (self.method, self.path) if self.method else ""
        text += "%d %s: %s" % (self.status_code, self.code, self.message)
        for f in self.fields:
            text += "; " + str(f)
        return text

    @property
    def kind(self) -> ErrorKind:  # type: ignore[override]
        return kind_for_status(self.status_code)

    @property
    def outcome_unknown(self) -> bool:
        """``True`` when the API said the registry or CA may already have done it."""
        return self.code in OUTCOME_UNKNOWN_CODES

    @property
    def retryable(self) -> bool:
        """Rate limits and server errors, unless the operation may already have happened."""
        if self.outcome_unknown:
            return False
        kind = self.kind
        return kind is ErrorKind.RATE_LIMITED or (kind is ErrorKind.SERVER and self.status_code != 501)

    @property
    def insufficient_balance(self) -> bool:
        """``True`` when the balance is too low for the operation."""
        return self.status_code == 402 or self.code in _INSUFFICIENT_BALANCE_CODES

    @property
    def hint(self) -> str:
        """A short suggestion for fixing the error, or ``""``."""
        if self.code == ErrorCode.INVALID_RESELLER:
            return ("The reseller ID is unknown, inactive or suspended in this environment. Check the reseller ID "
                    "(a UUID from the panel's API settings) and the environment (Client(environment=...)).")
        if self.code == ErrorCode.INVALID_API_KEY:
            return ("Production and OTE use different API keys. Make sure the key belongs to the environment the "
                    "client uses.")
        if self.code in (ErrorCode.MISSING_API_KEY, ErrorCode.MISSING_RESELLER_ID):
            return "Pass both the reseller ID and the API key to Client()."
        if self.code == ErrorCode.SUBRESELLER_NOT_ALLOWED:
            return "Sub-reseller accounts cannot use the API. Use the main reseller's credentials."
        if self.code == ErrorCode.RATE_LIMITED:
            return ("The API allows 5 requests/second per key (2/s for domain search). Slow down, or keep pacing "
                    "on (the default).")
        if self.outcome_unknown:
            return ("The operation may already have been carried out. Check the object's state before sending "
                    "the request again.")
        kind = self.kind
        if kind is ErrorKind.NOT_FOUND:
            return ("Check the spelling and the environment: production and OTE hold different domains. "
                    "client.domains.list() shows what this account holds.")
        if kind is ErrorKind.SERVER and self.correlation_id:
            return ("Server-side failure. If it persists, contact support and quote correlation ID %s."
                    % self.correlation_id)
        return ""


class AuthenticationError(APIError):
    """Wrong or missing credentials, or an unknown or suspended reseller."""


class NotFoundError(APIError):
    """The object does not exist, or is not yours."""


class ValidationError(APIError):
    """The API rejected the input (HTTP 400 or 422); see :attr:`fields`."""


class RejectedError(APIError):
    """A business rule refused the operation (HTTP 402 or 403)."""


class InsufficientBalanceError(RejectedError):
    """The balance is too low for the operation."""

    @property
    def kind(self) -> ErrorKind:  # type: ignore[override]
        return ErrorKind.REJECTED


class ConflictError(APIError):
    """The object is in a conflicting state (HTTP 409)."""


class RateLimitError(APIError):
    """Still rate limited after the automatic retries (HTTP 429)."""


class ServerError(APIError):
    """The API failed (HTTP 5xx); often transient."""


class OperationError(DomainNameAPIError):
    """The API answered 2xx but reported that the operation did not happen.

    For example ``"success": false`` for the registration of a domain that is
    not available.
    """

    kind = ErrorKind.REJECTED

    def __init__(self, method: str, path: str, code: str = "", message: str = "", correlation_id: str = ""):
        self.method = method
        self.path = path
        self.code = (code or "").strip()
        self.message = (message or "").strip()
        self.correlation_id = correlation_id
        text = self.message or "the API reported that the operation failed"
        if self.code:
            text = self.code + ": " + text
        super().__init__("%s %s: %s" % (method, path, text))


class NetworkError(DomainNameAPIError):
    """The request did not complete: DNS, TLS, proxy, timeout or connection reset.

    The underlying exception is ``__cause__``.
    """

    kind = ErrorKind.NETWORK

    def __init__(self, method: str, path: str, message: str, *, timeout: bool = False, safety: Any = None):
        self.method = method
        self.path = path
        self.message = message
        #: ``True`` when the request timed out.
        self.timeout = timeout
        self.safety = safety
        super().__init__("%s %s: %s" % (method, path, message))

    @property
    def outcome_unknown(self) -> bool:
        """``True`` unless the request was a read: it may have reached the API before failing."""
        return getattr(self.safety, "value", self.safety) != "read"

    @property
    def retryable(self) -> bool:
        return True


class DecodeError(DomainNameAPIError):
    """A successful response could not be decoded as JSON."""

    def __init__(self, method: str, path: str, message: str, body: bytes = b""):
        self.method = method
        self.path = path
        self.body = body
        super().__init__("%s %s: decode response: %s" % (method, path, message))


class WaitTimeoutError(DomainNameAPIError, TimeoutError):
    """A wait (``hosting.wait``) ran out of time; :attr:`last` is the last state seen."""

    kind = ErrorKind.UNKNOWN

    def __init__(self, message: str, last: Any = None):
        self.last = last
        super().__init__(message)


def kind_of(err: Optional[BaseException]) -> Optional[ErrorKind]:
    """Classify any exception: ``None`` for ``None``, :attr:`ErrorKind.UNKNOWN` for foreign ones."""
    if err is None:
        return None
    if isinstance(err, DomainNameAPIError):
        return err.kind
    return ErrorKind.UNKNOWN


def kind_for_status(status: int) -> ErrorKind:
    if status in (401, 301, 302):
        return ErrorKind.AUTH
    if status == 404:
        return ErrorKind.NOT_FOUND
    if status in (400, 422):
        return ErrorKind.VALIDATION
    if status in (402, 403):
        return ErrorKind.REJECTED
    if status == 409:
        return ErrorKind.CONFLICT
    if status == 429:
        return ErrorKind.RATE_LIMITED
    if status >= 500:
        return ErrorKind.SERVER
    return ErrorKind.UNKNOWN


# ---------------------------------------------------------------------------
# Response normalisation

#: The generic .NET exception text the API sometimes sends instead of a useful message.
_BOILERPLATE = re.compile(r"exception of type '[^']*' was thrown", re.IGNORECASE)


def _status_text(status: int) -> str:
    try:
        return HTTPStatus(status).phrase.lower()
    except ValueError:
        return "unexpected status"


def _error_class(status: int, code: str) -> type:
    if status == 402 or code in _INSUFFICIENT_BALANCE_CODES:
        return InsufficientBalanceError
    return {
        ErrorKind.AUTH: AuthenticationError,
        ErrorKind.NOT_FOUND: NotFoundError,
        ErrorKind.VALIDATION: ValidationError,
        ErrorKind.REJECTED: RejectedError,
        ErrorKind.CONFLICT: ConflictError,
        ErrorKind.RATE_LIMITED: RateLimitError,
        ErrorKind.SERVER: ServerError,
    }.get(kind_for_status(status), APIError)


def _header(headers: Mapping[str, str], name: str) -> str:
    lower = name.lower()
    for k, v in headers.items():
        if k.lower() == lower:
            return v
    return ""


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def api_error_from_response(method: str, path: str, status: int, headers: Mapping[str, str],
                            body: bytes) -> APIError:
    """Build the :class:`APIError` subclass for a non-2xx response."""
    correlation_id = _header(headers, "X-Correlation-Id")
    text = body.decode("utf-8", errors="replace").strip()
    common = dict(correlation_id=correlation_id, method=method, path=path, body=body)

    if status in (301, 302):
        # The gateway redirects to /Error/Suspend when the __reseller value is
        # unknown, inactive or suspended.
        return AuthenticationError(
            status, ErrorCode.INVALID_RESELLER,
            "authentication failed: the reseller ID is unknown, inactive or suspended", **common)
    if status == 429:
        message = "rate limit exceeded"
        retry_after = None
        raw_after = _header(headers, "Retry-After").strip()
        if raw_after:
            try:
                retry_after = float(raw_after)
                message += " (retry after %ss)" % raw_after
            except ValueError:
                pass
        return RateLimitError(status, ErrorCode.RATE_LIMITED, message, retry_after=retry_after, **common)

    code = ""
    message = ""
    details = ""
    fields: List[FieldError] = []
    data: Dict[str, Any] = {}
    parsed: Any = None
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
    if isinstance(parsed, dict):
        info = parsed.get("error") if isinstance(parsed.get("error"), dict) else parsed
        if info.get("code") is not None:
            code = _as_text(info.get("code"))
        message = _as_text(info.get("message"))
        details = _as_text(info.get("details"))
        if isinstance(info.get("data"), dict):
            data = info["data"]
        for ve in info.get("validationErrors") or []:
            if not isinstance(ve, dict):
                continue
            members = [str(m)[2:] if str(m).startswith("$.") else str(m) for m in (ve.get("members") or [])]
            fields.append(FieldError(",".join(members), _as_text(ve.get("message"))))
    elif text and not text.startswith("<"):
        # 401 bodies are plain text; HTML error pages are dropped.
        message = text

    if status == 401 and not code:
        lower = message.lower()
        if "api key is missing" in lower:
            code = ErrorCode.MISSING_API_KEY
        elif "resellerid is missing" in lower:
            code = ErrorCode.MISSING_RESELLER_ID
        elif "invalid api key" in lower:
            code = ErrorCode.INVALID_API_KEY
        elif "authorisation" in lower or "authorization" in lower:
            code = ErrorCode.SUBRESELLER_NOT_ALLOWED
        else:
            code = ErrorCode.UNAUTHORIZED

    # Replace boilerplate and code echoes with the details text.
    if _BOILERPLATE.search(message) or (message and message == code):
        d = details.strip()
        if d.startswith("Dna "):
            d = d[4:].strip()
        if d and not _BOILERPLATE.search(d) and d != code:
            message = d
        else:
            message = "the operation could not be completed"
    if not code:
        code = "HTTP_%d" % status
    if not message.strip():
        message = _status_text(status)

    cls = _error_class(status, code)
    return cls(status, code, message, details=details, fields=fields, data=data, **common)
