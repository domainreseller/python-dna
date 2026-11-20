"""Test helpers: a fake transport that records requests and answers with canned replies.

Use it to test your own code without touching the network::

    from domainnameapi.testing import FakeTransport, ok

    fake = FakeTransport(ok({"success": True, "info": {"domainName": "example.com", "status": "AVAILABLE"}}))
    client = fake.client()

    assert client.domains.search("example.com").available
    assert fake.last.json() == {"domainName": "example.com"}

Replies are used in order; the last one repeats. A reply can also be a
:class:`~domainnameapi.transport.TransportError` (raised, as a network
failure) or a callable that takes the :class:`RecordedRequest` and returns a reply.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Callable, Dict, List, Mapping, Optional, Union
from urllib.parse import parse_qs, urlsplit

from .transport import HttpRequest, HttpResponse, TransportError

__all__ = ["FakeTransport", "RecordedRequest", "Reply", "api_error", "ok", "TEST_API_KEY", "TEST_RESELLER_ID"]

TEST_RESELLER_ID = "00000000-0000-4000-8000-000000000001"
TEST_API_KEY = "test-api-key"


class Reply:
    """One canned response. ``body`` may be text, bytes, or a value encoded as JSON."""

    def __init__(self, status: int = 200, body: Any = b"", headers: Optional[Mapping[str, str]] = None):
        self.status = status
        if isinstance(body, bytes):
            self.body = body
        elif isinstance(body, str):
            self.body = body.encode("utf-8")
        else:
            self.body = json.dumps(body).encode("utf-8")
        self.headers = dict(headers or {})

    def __repr__(self) -> str:
        return "Reply(%d, %r)" % (self.status, self.body[:60])


def ok(body: Any = b"", headers: Optional[Mapping[str, str]] = None) -> Reply:
    """A 200 reply."""
    return Reply(200, body, headers)


def api_error(status: int, code: str, message: str, **extra: Any) -> Reply:
    """An error reply in the API's format (``{"error": {"code": ..., "message": ...}}``)."""
    error = {"code": code, "message": message, "details": None, "data": [], "validationErrors": None}
    error.update(extra)
    return Reply(status, {"error": error})


class RecordedRequest:
    """A request the fake transport received."""

    def __init__(self, request: HttpRequest):
        self.method = request.method
        self.url = request.url
        parts = urlsplit(request.url)
        #: The path without the query string, e.g. ``/api/v1/domains/info``.
        self.path = parts.path
        #: The query string; every key maps to the list of its values.
        self.query: Dict[str, List[str]] = parse_qs(parts.query, keep_blank_values=True)
        self.headers = dict(request.headers)
        self.body = request.body or b""
        self.timeout = request.timeout

    def header(self, name: str) -> str:
        lower = name.lower()
        for k, v in self.headers.items():
            if k.lower() == lower:
                return v
        return ""

    def param(self, name: str) -> Optional[str]:
        """The first value of a query parameter, or ``None``."""
        values = self.query.get(name)
        return values[0] if values else None

    def json(self) -> Any:
        """The body decoded as JSON (``None`` for no body)."""
        return json.loads(self.body) if self.body else None

    def __repr__(self) -> str:
        return "RecordedRequest(%r, %r)" % (self.method, self.url)


ReplyLike = Union[Reply, TransportError, Callable[[RecordedRequest], Any]]


class FakeTransport:
    """A transport that records requests and answers them with ``replies`` in order.

    The last reply repeats; with no replies every request gets an empty 200.
    Thread-safe.
    """

    def __init__(self, *replies: ReplyLike):
        self.replies: List[ReplyLike] = list(replies)
        #: Every request received, oldest first.
        self.requests: List[RecordedRequest] = []
        self._lock = threading.Lock()

    def send(self, request: HttpRequest) -> HttpResponse:
        recorded = RecordedRequest(request)
        with self._lock:
            self.requests.append(recorded)
            n = len(self.requests) - 1
            if not self.replies:
                reply: Any = Reply()
            else:
                reply = self.replies[min(n, len(self.replies) - 1)]
        if callable(reply) and not isinstance(reply, (Reply, TransportError)):
            reply = reply(recorded)
        if isinstance(reply, TransportError):
            raise reply
        if not isinstance(reply, Reply):
            reply = ok(reply)
        return HttpResponse(reply.status, reply.headers, reply.body)

    @property
    def last(self) -> RecordedRequest:
        """The last request received."""
        if not self.requests:
            raise AssertionError("no request reached the transport")
        return self.requests[-1]

    def client(self, **options: Any) -> Any:
        """A :class:`~domainnameapi.Client` using this transport, with pacing off."""
        from .client import Client

        options.setdefault("pacing", False)
        options.setdefault("base_url", "https://api.example.test")
        reseller_id = options.pop("reseller_id", TEST_RESELLER_ID)
        api_key = options.pop("api_key", TEST_API_KEY)
        return Client(reseller_id, api_key, transport=self, **options)
