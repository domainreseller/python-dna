"""The client: credentials, environments, sending, retries and pacing."""

from __future__ import annotations

import contextlib
import contextvars
import enum
import json
import logging
import os
import random
import re
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Sequence, Union
from urllib.parse import quote_plus, urlencode, urlsplit

from ._version import USER_AGENT, __version__
from .errors import (
    ConfigurationError,
    DecodeError,
    FieldError,
    InputError,
    MissingCredentialsError,
    NetworkError,
    ReadOnlyError,
    api_error_from_response,
)
from .model import decode_as
from .request import BaseRequest, Endpoint, Safety, Validator, _plain
from .transport import HttpRequest, HttpResponse, Transport, TransportError, UrllibTransport

from .account import AccountService
from .contacts import ContactService
from .dns import DNSService
from .dnssec import DNSSECService
from .domains import DomainService
from .hosting import HostingService
from .orders import OrderService
from .products import ProductService
from .ssl import SSLService

__all__ = [
    "ApiResponse",
    "Client",
    "DEFAULT_APP",
    "ENV_API_KEY",
    "ENV_APP",
    "ENV_APP_VERSION",
    "ENV_BASE_URL",
    "ENV_ENVIRONMENT",
    "ENV_RESELLER_ID",
    "ENV_TEST_MODE",
    "Environment",
    "OTE_URL",
    "PRODUCTION_URL",
    "PreparedRequest",
    "Quota",
    "TraceEvent",
    "correlation_id",
]

#: The live environment: real domains, real charges.
PRODUCTION_URL = "https://api.domainresellerapi.com"
#: The test environment (Operational Test & Evaluation): its own data and API key.
OTE_URL = "https://ote.domainresellerapi.com"

# Environment variables read by Client.from_env(); the same ones the dna CLI uses.
ENV_RESELLER_ID = "DNA_RESELLER_ID"
ENV_API_KEY = "DNA_API_KEY"
#: "production" or "ote".
ENV_ENVIRONMENT = "DNA_ENV"
#: "true" selects OTE.
ENV_TEST_MODE = "DNA_TEST_MODE"
#: Overrides the environment's URL.
ENV_BASE_URL = "DNA_BASE_URL"
#: The application using the SDK, sent as ``X-App`` (see ``Client(app_name=...)``).
ENV_APP = "DNA_APP"
#: That application's version, sent as ``X-Version`` (see ``Client(app_version=...)``).
ENV_APP_VERSION = "DNA_APP_VERSION"

#: The ``X-App`` value when the integration does not name itself.
DEFAULT_APP = "python"

log = logging.getLogger("domainnameapi")
log.addHandler(logging.NullHandler())


class Environment(str, enum.Enum):
    """The API deployment a client talks to."""

    #: The live environment (the default).
    PRODUCTION = "production"
    #: The test environment. Use your OTE API key with it.
    OTE = "ote"

    def __str__(self) -> str:
        return str(self.value)

    @property
    def base_url(self) -> str:
        return OTE_URL if self is Environment.OTE else PRODUCTION_URL

    @classmethod
    def parse(cls, value: Union["Environment", str, bool, None]) -> "Environment":
        """Accept ``"production"``/``"prod"``/``"live"``, ``"ote"``/``"test"``/``"sandbox"``.

        Test-mode flags as panels and the other DomainNameAPI SDKs store them
        work too: ``True``, ``"true"``, ``"1"``, ``"on"``, ``"yes"`` mean OTE;
        ``False``, ``"false"``, ``"0"``, ``"off"``, ``"no"`` mean production.
        """
        if isinstance(value, Environment):
            return value
        if isinstance(value, bool):
            return cls.OTE if value else cls.PRODUCTION
        text = (value or "").strip().lower()
        if text in ("", "production", "prod", "live", "false", "0", "off", "no"):
            return cls.PRODUCTION
        if text in ("ote", "test", "testing", "sandbox", "true", "1", "on", "yes"):
            return cls.OTE
        raise ConfigurationError('unknown environment %r (use "production" or "ote")' % value)


# ---------------------------------------------------------------------------
# Responses and tracing


@dataclass(frozen=True)
class Quota:
    """The API's soft-quota headers.

    The quota never rejects requests: once ``used`` exceeds ``limit`` the API
    delays each response (by ``delay`` seconds, at most 5) until points decay
    by 20% per minute. Lookups cost 1 point, everything else 10.
    """

    #: The area: domain, contact, ssl, products, order, deposit, hosting.
    scope: str
    #: Points this request cost.
    cost: float
    #: Points in the bucket after this request.
    used: float
    #: Where slowing down starts (200).
    limit: float
    #: Seconds this response was held back.
    delay: float
    #: Seconds until the bucket is back under the limit.
    reset: float

    @classmethod
    def from_headers(cls, response: HttpResponse) -> Optional["Quota"]:
        if not response.header("X-Quota-Limit") and not response.header("X-Quota-Used"):
            return None

        def num(name: str) -> float:
            try:
                return float(response.header(name).strip())
            except ValueError:
                return 0.0

        return cls(response.header("X-Quota-Scope"), num("X-Quota-Cost"), num("X-Quota-Used"),
                   num("X-Quota-Limit"), num("X-Quota-Delay"), num("X-Quota-Reset"))


@dataclass
class ApiResponse:
    """A completed exchange: the decoded value plus what the HTTP layer saw."""

    #: The decoded result, as ``client.send`` returns it.
    value: Any
    #: The HTTP status of the final attempt.
    status_code: int
    #: The response headers.
    headers: Dict[str, str]
    #: The raw response body.
    body: bytes
    #: Identifies the request; quote it when contacting support.
    correlation_id: str
    #: The soft-quota state after the request, or ``None``.
    quota: Optional[Quota]
    #: Total seconds, including retries and pacing.
    duration: float
    #: The number of HTTP attempts.
    attempts: int

    def json(self) -> Any:
        """The response body decoded as JSON (``None`` for an empty body)."""
        return json.loads(self.body) if self.body.strip() else None


@dataclass(frozen=True)
class TraceEvent:
    """One step of a request, for logging, metrics or error reporting. It never holds the API key."""

    #: ``"request"`` (an attempt is about to be sent), ``"response"`` (an attempt
    #: finished, with a status or an error) or ``"retry"`` (the client waits and tries again).
    kind: str
    method: str
    url: str
    safety: Safety
    correlation_id: str
    #: 1-based.
    attempt: int
    #: 0 before a response or after a transport error.
    status_code: int = 0
    #: Seconds spent on this attempt.
    duration: float = 0.0
    #: For ``"retry"``: seconds the client waits.
    wait: float = 0.0
    #: The request or response body, truncated to 16 KiB. It can hold contact
    #: details and auth codes: mask it before storing it.
    body: bytes = b""
    quota: Optional[Quota] = None
    error: Optional[BaseException] = None


class PreparedRequest:
    """A validated request ready to send (see :meth:`Client.prepare`).

    ``headers`` carry your credentials; ``repr`` masks the API key.
    """

    __slots__ = ("request", "method", "url", "path", "headers", "body", "safety", "idempotent")

    def __init__(self, request: BaseRequest, endpoint: Endpoint, url: str, headers: Dict[str, str],
                 body: Optional[bytes]):
        self.request = request
        self.method = endpoint.method
        self.path = endpoint.path
        self.url = url
        self.headers = headers
        self.body = body
        self.safety = endpoint.safety
        self.idempotent = endpoint.idempotent

    def __repr__(self) -> str:
        return "<PreparedRequest %s %s (%s)>" % (self.method, self.url, self.safety)


_correlation: contextvars.ContextVar[str] = contextvars.ContextVar("domainnameapi_correlation_id", default="")


@contextlib.contextmanager
def correlation_id(value: str) -> Iterator[str]:
    """Send the requests made inside the block with ``X-Correlation-ID: value``.

    Without it the client generates one per request. The API logs it: quote it
    when contacting support, or use your own to tie API calls to your logs::

        with dna.correlation_id("order-4711"):
            client.domains.renew("example.com", 1)
    """
    token = _correlation.set((value or "").strip())
    try:
        yield value
    finally:
        _correlation.reset(token)


def _request_name(request: Any) -> str:
    return type(request).__name__ if request is not None else "request"


def _truncate(body: Optional[bytes]) -> bytes:
    if not body:
        return b""
    limit = 16 << 10
    return body if len(body) <= limit else body[:limit] + "…(truncated)".encode("utf-8")


def _json_default(value: Any) -> Any:
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, (set, frozenset, tuple)):
        return list(value)
    raise TypeError("%s is not JSON serializable" % type(value).__name__)


def _encode_query(query: Any) -> str:
    if not query:
        return ""
    pairs = query.items() if isinstance(query, Mapping) else query
    out = []
    for key, value in pairs:
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            out.extend((key, _plain(v)) for v in value if v is not None)
        else:
            out.append((key, _plain(value)))
    return urlencode(out, quote_via=quote_plus)


def _normalize_app(value: Optional[str]) -> str:
    """Lowercase, keep only ``[a-z0-9._-]``; empty means :data:`DEFAULT_APP`."""
    app = re.sub(r"[^a-z0-9._-]", "", (value or "").strip().lower())
    return app or DEFAULT_APP


def _normalize_version(value: Optional[str]) -> str:
    """Keep digits and dots, trim surrounding dots; empty means the SDK version."""
    version = re.sub(r"[^0-9.]", "", value or "").strip(".")
    return version or re.sub(r"[^0-9.]", "", __version__).strip(".")


def _backoff(attempt: int) -> float:
    return 0.5 * (2 ** (attempt - 1)) + random.uniform(0, 0.25)


def _retry_after(response: HttpResponse, attempt: int) -> float:
    value = response.header("Retry-After").strip()
    if value:
        try:
            seconds = float(value)
            if seconds >= 0:
                return seconds + 0.05
        except ValueError:
            try:
                when = parsedate_to_datetime(value)
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                wait = (when - datetime.now(timezone.utc)).total_seconds()
                if wait > 0:
                    return wait
            except (TypeError, ValueError, IndexError):
                pass
    return _backoff(attempt)


class _Pacer:
    """Spaces requests per rate-limit class (thread-safe)."""

    def __init__(self, clock: Callable[[], float], sleep: Callable[[float], None]):
        self._lock = threading.Lock()
        self._next: Dict[str, float] = {}
        self._clock = clock
        self._sleep = sleep

    @staticmethod
    def pace_class(path: str):
        p = path.lower()
        if p.startswith("/api/v1/domains/zones"):
            return "zones", 1.0
        if p in ("/api/v1/domains/search", "/api/v1/domains/bulk-search"):
            return "search", 0.5
        if p == "/api/v1/domains/info" or p.startswith("/api/v1/products/tlds"):
            return "", 0.0  # not rate limited
        return "general", 0.2

    def wait(self, path: str) -> None:
        cls, gap = self.pace_class(path)
        if not gap:
            return
        with self._lock:
            now = self._clock()
            due = max(self._next.get(cls, now), now)
            self._next[cls] = due + gap
            if cls == "search":  # searches also count against the overall budget
                self._next["general"] = max(self._next.get("general", 0.0), due + 0.2)
        if due > now:
            self._sleep(due - now)


# ---------------------------------------------------------------------------
# Client


class Client:
    """A client for the DomainNameAPI reseller REST API.

    The services group the operations the same way the ``dna`` CLI groups its
    commands: ``dna domain info`` is ``client.domains.info``, ``dna dns add``
    is ``client.dns.add``.

    :param reseller_id: the reseller ID (a UUID) from the reseller panel, API settings.
    :param api_key: the API key from the same page. Production and OTE have different keys;
        panel login details do not work.
    :param environment: ``"production"`` (default) or ``"ote"``, or an :class:`Environment`.
    :param base_url: a custom base URL (a proxy or a test server); overrides ``environment``.
    :param timeout: seconds per HTTP attempt (default 60). Keep it well above 5: over the
        soft quota the API delays responses by up to 5 seconds instead of rejecting them.
    :param retries: how often a failed request is retried (default 2). 429 answers are always
        retried; network errors and 502/503/504 only for requests that are safe to repeat.
    :param pacing: space requests to stay under the rate limits (default ``True``).
    :param read_only: block every request that would change something.
    :param currency: currency (``"USD"``, ``"TRY"``) of search and catalogue prices when a call
        does not name one; without it the API uses the account's currency.
    :param user_agent: your product, put in front of the User-Agent, e.g. ``"my-panel/1.4"``.
    :param app_name: the application using the SDK, sent as ``X-App`` with every request, e.g.
        ``"whmcs"``. Lowercased; only ``a-z``, ``0-9``, ``.``, ``_`` and ``-`` are kept. Empty or
        nothing left means ``"python"``.
    :param app_version: that application's version, sent as ``X-Version``. Only digits and dots
        are kept (``"V2.0.20-beta"`` becomes ``"2.0.20"``); empty means this SDK's version.
    :param transport: an object with ``send(HttpRequest) -> HttpResponse``; default
        :class:`~domainnameapi.transport.UrllibTransport`.
    :param trace: a callable (or a list of them) called with every :class:`TraceEvent`.
    :param logger: where exchanges are logged (default the ``"domainnameapi"`` logger):
        requests and responses at DEBUG, retries at WARNING.

    A client is safe to share between threads. Create one and reuse it: it
    paces requests across threads.
    """

    def __init__(
        self,
        reseller_id: str,
        api_key: str,
        *,
        environment: Union[Environment, str, bool] = Environment.PRODUCTION,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        retries: int = 2,
        pacing: bool = True,
        read_only: bool = False,
        currency: Optional[str] = None,
        user_agent: Optional[str] = None,
        app_name: Optional[str] = None,
        app_version: Optional[str] = None,
        transport: Optional[Transport] = None,
        trace: Union[Callable[[TraceEvent], Any], Sequence[Callable[[TraceEvent], Any]], None] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self._reseller_id = (reseller_id or "").strip()
        self._api_key = (api_key or "").strip()
        if not self._reseller_id or not self._api_key:
            raise MissingCredentialsError()
        self._environment = Environment.parse(environment)
        self._base_url = self._check_base_url(base_url or self._environment.base_url)
        if timeout is not None and timeout <= 0:
            raise ConfigurationError("timeout must be positive")
        self._timeout = float(timeout or 60.0)
        self._retries = max(0, int(retries))
        self._max_wait = 30.0
        self._read_only = bool(read_only)
        self._currency = (currency or "").strip().upper()
        product = (user_agent or "").strip()
        self._user_agent = product + " " + USER_AGENT if product else USER_AGENT
        self._app_name = _normalize_app(app_name)
        self._app_version = _normalize_version(app_version)
        self._transport: Transport = transport if transport is not None else UrllibTransport()
        if trace is None:
            self._trace: List[Callable[[TraceEvent], Any]] = []
        elif callable(trace):
            self._trace = [trace]
        else:
            self._trace = [fn for fn in trace if fn is not None]
        self._log = logger or log
        self._clock = time.monotonic
        self._sleep = time.sleep
        self._pacer: Optional[_Pacer] = _Pacer(lambda: self._clock(), lambda s: self._sleep(s)) if pacing else None

        #: Balance, reseller profile and balance transactions (``dna account``).
        self.account = AccountService(self)
        #: Reusable contact handles (``dna contact``).
        self.contacts = ContactService(self)
        #: Search, register, renew, transfer and manage domains (``dna domain``).
        self.domains = DomainService(self)
        #: Zone records of domains on the platform nameservers (``dna dns``).
        self.dns = DNSService(self)
        #: DS records of domains (``dna dnssec``).
        self.dnssec = DNSSECService(self)
        #: SSL certificates (``dna ssl``).
        self.ssl = SSLService(self)
        #: Web hosting packages and services (``dna hosting``).
        self.hosting = HostingService(self)
        #: Orders and their lines (``dna order``).
        self.orders = OrderService(self)
        #: The catalogue and prices of TLDs, SSL and other products (``dna product``).
        self.products = ProductService(self)

    @classmethod
    def from_env(cls, **options: Any) -> "Client":
        """Create a client from the environment variables the ``dna`` CLI uses.

        ``DNA_RESELLER_ID``, ``DNA_API_KEY``, ``DNA_ENV`` (``production`` or
        ``ote``; or ``DNA_TEST_MODE=true``) and ``DNA_BASE_URL``, plus
        ``DNA_APP`` and ``DNA_APP_VERSION`` for ``app_name`` and ``app_version``.
        Keyword arguments are passed to :class:`Client` and win over the environment.
        """
        env = os.environ
        reseller_id = options.pop("reseller_id", None) or env.get(ENV_RESELLER_ID, "")
        api_key = options.pop("api_key", None) or env.get(ENV_API_KEY, "")
        if not reseller_id.strip() or not api_key.strip():
            raise MissingCredentialsError("%s and %s must both be set" % (ENV_RESELLER_ID, ENV_API_KEY))
        if "environment" not in options:
            options["environment"] = env.get(ENV_ENVIRONMENT) or env.get(ENV_TEST_MODE) or Environment.PRODUCTION
        if "base_url" not in options and env.get(ENV_BASE_URL, "").strip():
            options["base_url"] = env[ENV_BASE_URL]
        if "app_name" not in options and env.get(ENV_APP, "").strip():
            options["app_name"] = env[ENV_APP]
        if "app_version" not in options and env.get(ENV_APP_VERSION, "").strip():
            options["app_version"] = env[ENV_APP_VERSION]
        return cls(reseller_id, api_key, **options)

    # -- properties ---------------------------------------------------------

    @property
    def base_url(self) -> str:
        """The base URL requests go to."""
        return self._base_url

    @property
    def environment(self) -> Environment:
        """OTE when the client talks to the test environment, production otherwise."""
        return Environment.OTE if self._base_url == OTE_URL else Environment.PRODUCTION

    @property
    def read_only(self) -> bool:
        """``True`` when the client blocks everything that is not a read."""
        return self._read_only

    @property
    def currency(self) -> str:
        """The default price currency, or ``""`` for the account's."""
        return self._currency

    @property
    def app_name(self) -> str:
        """The ``X-App`` value sent with every request (``"python"`` by default)."""
        return self._app_name

    @property
    def app_version(self) -> str:
        """The ``X-Version`` value sent with every request (this SDK's version by default)."""
        return self._app_version

    @property
    def reseller_id(self) -> str:
        return self._reseller_id

    def __repr__(self) -> str:
        return "Client(environment=%r, base_url=%r, read_only=%r)" % (
            str(self.environment), self._base_url, self._read_only)

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the transport when it has a ``close`` method."""
        closer = getattr(self._transport, "close", None)
        if callable(closer):
            closer()

    @staticmethod
    def _check_base_url(raw: str) -> str:
        url = (raw or "").strip().rstrip("/")
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ConfigurationError("invalid base URL %r (want e.g. %s)" % (raw, PRODUCTION_URL))
        return url

    # -- sending -------------------------------------------------------------

    def prepare(self, request: BaseRequest) -> PreparedRequest:
        """Validate ``request`` and build what :meth:`send` would send, without sending it.

        Use it to log or review a billable request before it goes out. The
        result carries your credentials in its headers.
        """
        return self._prepare(request, _correlation.get() or uuid.uuid4().hex)

    def _prepare(self, request: BaseRequest, corr_id: str) -> PreparedRequest:
        if request is None:
            raise TypeError("request must not be None")
        name = _request_name(request)
        ep = request.endpoint()
        method = (ep.method or "GET").strip().upper()
        if method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            raise ConfigurationError("%s: unsupported method %r" % (name, ep.method))
        path = ep.path if ep.path.startswith("/") else "/" + ep.path
        ep = Endpoint(method, path, ep.safety, ep.idempotent)

        v = Validator()
        try:
            request.validate(v)
        except InputError:
            raise
        except ValueError as err:
            v.add("", str(err))
        v.raise_if_invalid(name)

        if self._read_only and ep.safety is not Safety.READ:
            raise ReadOnlyError(name, ep.method, ep.path, ep.safety)

        body_value = request.body()
        body: Optional[bytes] = None
        if body_value is not None:
            try:
                body = json.dumps(body_value, ensure_ascii=False, separators=(",", ":"),
                                  default=_json_default).encode("utf-8")
            except (TypeError, ValueError) as err:
                raise InputError(name, [FieldError("body", "cannot be encoded as JSON: %s" % err)]) from err

        url = self._base_url + ep.path
        qs = _encode_query(request.query())
        if qs:
            url += "?" + qs
        headers = {
            "Accept": "application/json",
            "User-Agent": self._user_agent,
            "X-API-KEY": self._api_key,
            "__reseller": self._reseller_id,
            "X-Correlation-ID": corr_id,
            "X-App": self._app_name,
            "X-Version": self._app_version,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        return PreparedRequest(request, ep, url, headers, body)

    def send(self, request: BaseRequest) -> Any:
        """Validate ``request``, send it and return the decoded answer.

        The answer is decoded with the request's ``response`` spec: a model, a
        list or page of models, or the plain JSON (``dict``, ``list``, ``None``
        for an empty body). Works for the request classes of this package and
        for your own :class:`~domainnameapi.BaseRequest` subclasses.

        :raises InputError: validation rejected the request; nothing was sent.
        :raises ReadOnlyError: the client is read-only; nothing was sent.
        :raises APIError: the API answered with a non-2xx status (see its subclasses).
        :raises NetworkError: the request did not complete.
        """
        return self.send_with_response(request).value

    def send_with_response(self, request: BaseRequest) -> ApiResponse:
        """Like :meth:`send`, but return the :class:`ApiResponse` with status, headers,
        correlation ID, quota, duration and attempts."""
        corr_id = _correlation.get() or uuid.uuid4().hex
        prepared = self._prepare(request, corr_id)
        start = self._clock()
        attempt = 0
        while True:
            attempt += 1
            if self._pacer is not None:
                self._pacer.wait(prepared.path)
            self._emit("request", prepared, corr_id, attempt, body=_truncate(prepared.body))
            http_request = HttpRequest(prepared.method, prepared.url, dict(prepared.headers), prepared.body,
                                       self._timeout)
            t0 = self._clock()
            try:
                response = self._transport.send(http_request)
            except TransportError as err:
                self._emit("response", prepared, corr_id, attempt, duration=self._clock() - t0, error=err)
                if prepared.idempotent and err.retryable and attempt <= self._retries:
                    wait = _backoff(attempt)
                    self._emit("retry", prepared, corr_id, attempt, wait=wait, error=err)
                    self._sleep(wait)
                    continue
                raise NetworkError(prepared.method, prepared.path, err.message, timeout=err.timeout,
                                   safety=prepared.safety) from err

            quota = Quota.from_headers(response)
            self._emit("response", prepared, corr_id, attempt, status=response.status,
                       duration=self._clock() - t0, body=_truncate(response.body), quota=quota)

            if 200 <= response.status < 300:
                data = None
                if response.body.strip():
                    try:
                        data = json.loads(response.body.decode("utf-8-sig"))
                    except ValueError as err:
                        raise DecodeError(prepared.method, prepared.path, str(err), response.body) from err
                decode = getattr(request, "decode", None)
                value = decode(data) if callable(decode) else decode_as(getattr(request, "response", None), data)
                return ApiResponse(
                    value=value,
                    status_code=response.status,
                    headers=response.headers,
                    body=response.body,
                    correlation_id=response.header("X-Correlation-Id") or corr_id,
                    quota=quota,
                    duration=self._clock() - start,
                    attempts=attempt,
                )

            retry = response.status == 429 or (prepared.idempotent and response.status in (502, 503, 504))
            if retry and attempt <= self._retries:
                wait = _retry_after(response, attempt)
                if wait <= self._max_wait:
                    self._emit("retry", prepared, corr_id, attempt, status=response.status, wait=wait)
                    self._sleep(wait)
                    continue
            err = api_error_from_response(prepared.method, prepared.path, response.status, response.headers,
                                          response.body)
            if not err.correlation_id:
                err.correlation_id = corr_id
            raise err

    def _emit(self, kind: str, prepared: PreparedRequest, corr_id: str, attempt: int, *, status: int = 0,
              duration: float = 0.0, wait: float = 0.0, body: bytes = b"", quota: Optional[Quota] = None,
              error: Optional[BaseException] = None) -> None:
        logger = self._log
        if kind == "retry":
            logger.warning("dna: retrying %s %s in %.2fs (attempt %d, status %s, error %s, correlation_id %s)",
                           prepared.method, prepared.url, wait, attempt, status or "-", error or "-", corr_id)
        elif logger.isEnabledFor(logging.DEBUG):
            if kind == "request":
                logger.debug("dna: request %s %s (attempt %d, correlation_id %s)", prepared.method, prepared.url,
                             attempt, corr_id)
            elif error is not None:
                logger.debug("dna: %s %s failed after %.3fs: %s (correlation_id %s)", prepared.method,
                             prepared.url, duration, error, corr_id)
            else:
                logger.debug("dna: response %s %s -> %d in %.3fs (correlation_id %s)", prepared.method,
                             prepared.url, status, duration, corr_id)
        if not self._trace:
            return
        event = TraceEvent(kind, prepared.method, prepared.url, prepared.safety, corr_id, attempt, status,
                           duration, wait, body, quota, error)
        for fn in self._trace:
            fn(event)

