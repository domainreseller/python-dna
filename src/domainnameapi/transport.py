"""HTTP transport.

The client sends every attempt through a *transport*: any object with a
``send(request: HttpRequest) -> HttpResponse`` method that raises
:class:`TransportError` when no HTTP response arrived. The default
:class:`UrllibTransport` uses only the standard library. Plug in your own to
use ``requests``, ``httpx``, a proxy library or a test double (see
:mod:`domainnameapi.testing`)::

    import requests

    class RequestsTransport:
        def __init__(self):
            self.session = requests.Session()

        def send(self, req):
            try:
                r = self.session.request(req.method, req.url, headers=req.headers, data=req.body,
                                         timeout=req.timeout, allow_redirects=False)
            except requests.RequestException as err:
                raise TransportError(str(err), timeout=isinstance(err, requests.Timeout)) from err
            return HttpResponse(r.status_code, dict(r.headers), r.content)

Redirects must not be followed: the API answers 302 for an unknown or
suspended reseller ID, which the client turns into an authentication error.
"""

from __future__ import annotations

import functools
import http.client
import socket
import ssl
import time
import urllib.error
import urllib.request
from typing import Dict, Mapping, Optional, Protocol

__all__ = ["HttpRequest", "HttpResponse", "Transport", "TransportError", "UrllibTransport"]


class HttpRequest:
    """One HTTP attempt. ``headers`` carry the API key: never log them as they are."""

    __slots__ = ("method", "url", "headers", "body", "timeout")

    def __init__(self, method: str, url: str, headers: Dict[str, str], body: Optional[bytes] = None,
                 timeout: float = 60.0):
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body
        self.timeout = timeout

    def __repr__(self) -> str:
        return "HttpRequest(%r, %r)" % (self.method, self.url)


class HttpResponse:
    """The status, headers and raw body of one HTTP attempt."""

    __slots__ = ("status", "headers", "body")

    def __init__(self, status: int, headers: Optional[Mapping[str, str]] = None, body: bytes = b""):
        self.status = int(status)
        self.headers: Dict[str, str] = dict(headers or {})
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.body = body or b""

    def header(self, name: str) -> str:
        """A header value by case-insensitive name, or ``""``."""
        lower = name.lower()
        for k, v in self.headers.items():
            if k.lower() == lower:
                return v
        return ""

    def __repr__(self) -> str:
        return "HttpResponse(%d, %d bytes)" % (self.status, len(self.body))


class TransportError(Exception):
    """No HTTP response arrived: DNS, connect, TLS, timeout or a dropped connection."""

    def __init__(self, message: str, *, timeout: bool = False, retryable: bool = True):
        super().__init__(message)
        self.message = message
        #: ``True`` when the attempt timed out.
        self.timeout = timeout
        #: ``False`` for failures that repeat identically (certificate problems, a bad URL).
        self.retryable = retryable


class Transport(Protocol):
    """What the client needs from a transport."""

    def send(self, request: HttpRequest) -> HttpResponse:  # pragma: no cover - protocol
        ...


# ---------------------------------------------------------------------------
# urllib implementation


class _ConnectTimeoutMixin:
    """Use a shorter timeout for connect (and the TLS handshake) than for the rest."""

    def __init__(self, *args, **kwargs):
        self._connect_timeout = kwargs.pop("connect_timeout", None)
        super().__init__(*args, **kwargs)

    def connect(self):
        total = self.timeout
        if self._connect_timeout is not None:
            self.timeout = min(self._connect_timeout, total) if total else self._connect_timeout
        try:
            super().connect()
        finally:
            self.timeout = total
        if self.sock is not None:
            self.sock.settimeout(total)


class _HTTPConnection(_ConnectTimeoutMixin, http.client.HTTPConnection):
    pass


class _HTTPSConnection(_ConnectTimeoutMixin, http.client.HTTPSConnection):
    pass


class _HTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, connect_timeout: float):
        super().__init__()
        self._connect_timeout = connect_timeout

    def http_open(self, req):
        return self.do_open(functools.partial(_HTTPConnection, connect_timeout=self._connect_timeout), req)


class _HTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, connect_timeout: float, context: ssl.SSLContext):
        super().__init__(context=context)
        self._connect_timeout = connect_timeout
        self._ctx = context

    def https_open(self, req):
        return self.do_open(functools.partial(_HTTPSConnection, connect_timeout=self._connect_timeout), req,
                            context=self._ctx)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _read_body(fp, deadline: float) -> bytes:
    chunks = []
    while True:
        if time.monotonic() > deadline:
            raise socket.timeout("timed out while reading the response body")
        chunk = fp.read(65536)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _classify(exc: BaseException) -> TransportError:
    reason: BaseException = exc
    if isinstance(exc, urllib.error.URLError) and not isinstance(exc, urllib.error.HTTPError):
        if isinstance(exc.reason, BaseException):
            reason = exc.reason
        elif exc.reason:
            reason = OSError(str(exc.reason))
    text = str(reason) or reason.__class__.__name__
    if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in text.lower():
        return TransportError("timeout: " + text, timeout=True)
    if isinstance(reason, socket.gaierror):
        return TransportError("could not resolve host: " + text)
    if isinstance(reason, ssl.SSLCertVerificationError):
        return TransportError("TLS certificate problem: " + text, retryable=False)
    if isinstance(reason, ssl.SSLError):
        return TransportError("TLS error: " + text)
    if isinstance(reason, ConnectionRefusedError):
        return TransportError("connection refused: " + text)
    if isinstance(reason, http.client.RemoteDisconnected):
        return TransportError("empty reply from server")
    if isinstance(reason, http.client.IncompleteRead):
        return TransportError("connection closed before the response was complete")
    if isinstance(reason, ConnectionResetError):
        return TransportError("connection reset by peer")
    return TransportError(text)


class UrllibTransport:
    """Standard-library transport (``urllib.request``).

    Redirects are not followed, the connection (and TLS handshake) must be up
    within ``connect_timeout`` seconds and each attempt must finish within the
    request's timeout. Proxy environment variables (``HTTPS_PROXY`` ...) are
    honoured.

    :param connect_timeout: seconds for connect and TLS handshake (default 10).
    :param ssl_context: a custom :class:`ssl.SSLContext`, e.g. with your own CA bundle.
    """

    def __init__(self, connect_timeout: float = 10.0, ssl_context: Optional[ssl.SSLContext] = None):
        self.connect_timeout = connect_timeout
        self.ssl_context = ssl_context or ssl.create_default_context()
        self._opener = urllib.request.build_opener(
            _NoRedirect(),
            _HTTPHandler(connect_timeout),
            _HTTPSHandler(connect_timeout, self.ssl_context),
        )

    def send(self, request: HttpRequest) -> HttpResponse:
        try:
            req = urllib.request.Request(request.url, data=request.body, method=request.method)
        except ValueError as err:
            raise TransportError("invalid URL: %s" % err, retryable=False) from err
        for name, value in request.headers.items():
            req.add_header(name, value)
        deadline = time.monotonic() + request.timeout
        try:
            try:
                resp = self._opener.open(req, timeout=request.timeout)
            except urllib.error.HTTPError as err:
                # Non-2xx statuses are responses, not transport failures.
                body = _read_body(err, deadline) if err.fp is not None else b""
                headers = dict(err.headers.items()) if err.headers is not None else {}
                err.close()
                return HttpResponse(err.code, headers, body)
            with resp:
                return HttpResponse(resp.status, dict(resp.headers.items()), _read_body(resp, deadline))
        except TransportError:
            raise
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            raise _classify(exc) from exc
