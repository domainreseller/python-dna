"""Requests: :class:`BaseRequest` and the helpers request classes use.

Every API operation is a request class, e.g. ``DomainInfoRequest`` or
``DNSAddRequest``. They all subclass :class:`BaseRequest`, which supplies the
defaults (no query string, no body, nothing to validate). A request declares
where it goes with class attributes and overrides what it needs::

    from dataclasses import dataclass

    from domainnameapi import BaseRequest, Safety, Validator

    @dataclass
    class DomainRenewRequest(BaseRequest):
        method = "POST"
        path = "/api/v1/domains/renew"
        safety = Safety.BILLABLE

        domain_name: str = ""
        years: int = 1

        def body(self):
            return {"domainName": self.domain_name.strip(), "period": self.years}

        def validate(self, v: Validator) -> None:
            v.required("domain_name", self.domain_name)
            v.between("years", self.years, 1, 10, optional=False)

Send any request, including your own, with ``client.send(request)``.
"""

from __future__ import annotations

import enum
import string
from datetime import datetime, timezone
from collections.abc import Iterable as _IterableABC
from typing import Any, ClassVar, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
from urllib.parse import quote

from .errors import FieldError, InputError
from .model import decode_as

__all__ = ["BaseRequest", "Body", "Endpoint", "Query", "Safety", "Validator"]


class Safety(str, enum.Enum):
    """What a request does to your account.

    The client uses it to decide what may be retried and what a read-only
    client blocks.
    """

    #: No side effects, even when the HTTP method is POST or PUT (a domain search is a POST).
    READ = "read"
    #: Changes something, free of charge and reversibly (DNS records, locks, contacts, nameservers).
    WRITE = "write"
    #: Deletes something or is hard to undo (record deletion, DNSSEC removal, revocation).
    DESTRUCTIVE = "destructive"
    #: Charges the reseller balance (registrations, renewals, transfers, SSL and hosting orders).
    BILLABLE = "billable"

    def __str__(self) -> str:
        return str(self.value)


class Endpoint:
    """Where a request goes and what kind of request it is."""

    __slots__ = ("method", "path", "safety", "idempotent")

    def __init__(self, method: str, path: str, safety: Safety = Safety.READ, idempotent: bool = False):
        #: The HTTP method: GET, POST, PUT or DELETE.
        self.method = method
        #: The escaped path below the base URL, e.g. ``/api/v1/domains/info``.
        self.path = path
        #: The safety class.
        self.safety = safety = Safety(safety)
        #: ``True`` when sending the request twice is harmless. Reads always are.
        self.idempotent = idempotent or safety is Safety.READ

    def __repr__(self) -> str:
        return "Endpoint(%r, %r, %s)" % (self.method, self.path, self.safety)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Endpoint) and (self.method, self.path, self.safety, self.idempotent) == (
            other.method, other.path, other.safety, other.idempotent)


class Validator:
    """Collects field problems in :meth:`BaseRequest.validate`.

    The client raises :class:`~domainnameapi.InputError` with all of them,
    and sends nothing, when there is at least one.
    """

    def __init__(self) -> None:
        self.errors: List[FieldError] = []

    def __bool__(self) -> bool:
        return bool(self.errors)

    def add(self, field: str, message: str) -> None:
        """Record a problem."""
        self.errors.append(FieldError(field, message))

    def check(self, ok: Any, field: str, message: str) -> bool:
        """Record ``message`` unless ``ok``; returns ``ok``."""
        if not ok:
            self.add(field, message)
        return bool(ok)

    def required(self, field: str, value: Any) -> bool:
        """The value must not be ``None`` or blank."""
        ok = value is not None and (not isinstance(value, str) or value.strip() != "")
        return self.check(ok, field, "is required")

    def required_list(self, field: str, values: Optional[Iterable[Any]]) -> bool:
        """The list must hold at least one non-blank value."""
        return self.check(len(non_blank(values)) > 0, field, "needs at least one value")

    def between(self, field: str, value: Optional[int], low: int, high: int, *, optional: bool = True) -> bool:
        """The number must be in ``[low, high]``; with ``optional``, 0 and ``None`` mean "not set"."""
        if optional and not value:
            return True
        ok = isinstance(value, int) and not isinstance(value, bool) and low <= value <= high
        return self.check(ok, field, "must be between %d and %d" % (low, high))

    def max_length(self, field: str, value: Optional[str], limit: int) -> bool:
        """The string must have at most ``limit`` characters."""
        return self.check(value is None or len(value) <= limit, field, "must be at most %d characters" % limit)

    def enum(self, field: str, value: Any, enum_cls: Any, *, optional: bool = True) -> bool:
        """The value must be a member of ``enum_cls``, its name or its number."""
        if value is None or value == "":
            return self.check(optional, field, "is required")
        try:
            member = enum_cls.parse(value)
        except ValueError as err:
            self.add(field, str(err))
            return False
        if getattr(member, "is_known", True):
            return True
        self.add(field, "is not a known %s" % enum_cls.__name__)
        return False

    def raise_if_invalid(self, request: str) -> None:
        """Raise :class:`~domainnameapi.InputError` when problems were recorded."""
        if self.errors:
            raise InputError(request, self.errors)


#: A query string: a mapping (list values repeat the key) or a sequence of pairs.
QueryLike = Union[Mapping[str, Any], Sequence[Tuple[str, Any]]]


class BaseRequest:
    """Base class of every API request.

    Subclasses set the class attributes :attr:`method`, :attr:`path`,
    :attr:`safety` (and :attr:`idempotent`, :attr:`response` when needed) and
    override :meth:`query`, :meth:`body` and :meth:`validate` as needed. The
    request classes of this package are dataclasses; yours do not have to be.

    :attr:`path` may hold ``{placeholders}`` filled from the request's
    attributes, escaped: ``"/api/v1/contacts/{handle}"``.
    """

    #: The HTTP method: ``"GET"``, ``"POST"``, ``"PUT"`` or ``"DELETE"``.
    method: ClassVar[str] = "GET"
    #: The path below the base URL, e.g. ``"/api/v1/domains/info"``.
    path: ClassVar[str] = ""
    #: What the request does to your account.
    safety: ClassVar[Safety] = Safety.READ
    #: ``True`` when sending the request twice is harmless (reads always are).
    #: Only idempotent requests are retried after network errors and 5xx answers.
    idempotent: ClassVar[bool] = False
    #: How ``client.send`` decodes a successful answer: a
    #: :class:`~domainnameapi.model.Model` subclass, a converter such as
    #: ``list_of(RecordSet)`` or ``page_of(Domain)``, or ``None`` to return the JSON as is.
    response: ClassVar[Any] = None

    def endpoint(self) -> Endpoint:
        """The method, the path (placeholders filled in) and the safety class."""
        return Endpoint(self.method.upper(), self._fill_path(self.path), self.safety, self.idempotent)

    def query(self) -> Optional[QueryLike]:
        """The query string parameters, or ``None``."""
        return None

    def body(self) -> Any:
        """The value sent as the JSON body, or ``None`` for no body."""
        return None

    def validate(self, v: Validator) -> None:
        """Record problems with :class:`Validator`; nothing is sent when there are any."""

    def decode(self, data: Any) -> Any:
        """Turn the decoded JSON of a successful answer into the result ``client.send`` returns.

        The default uses :attr:`response`. Override it to post-process the answer.
        """
        return decode_as(self.response, data)

    def _fill_path(self, template: str) -> str:
        names = [name for _, name, _, _ in string.Formatter().parse(template) if name]
        if not names:
            return template
        values = {name: quote(str(getattr(self, name, "") or "").strip(), safe="") for name in names}
        return template.format(**values)

    def __str__(self) -> str:
        ep = self.endpoint()
        return "%s %s" % (ep.method, ep.path)


# ---------------------------------------------------------------------------
# Helpers for request classes


def non_blank(values: Optional[Iterable[Any]]) -> List[str]:
    """Strip every value and drop the blank ones. A single string is one value."""
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    out = []
    for v in values:
        s = str(v).strip() if v is not None else ""
        if s:
            out.append(s)
    return out


def as_list(values: Any) -> list:
    """``None`` gives ``[]``, a single value (string, model, ...) gives ``[value]``."""
    if values is None:
        return []
    if isinstance(values, (str, bytes, dict)) or not isinstance(values, _IterableABC):
        return [values]
    return list(values)


def strip(value: Optional[str]) -> str:
    return (value or "").strip()


class Body(dict):
    """A JSON object body. Keys given to the constructor are always sent;
    :meth:`set` adds a key only when the value is not empty."""

    def set(self, key: str, value: Any) -> "Body":
        if value is None:
            return self
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return self
        elif isinstance(value, bool):
            pass
        elif isinstance(value, int) and value == 0:
            return self
        elif isinstance(value, (list, tuple, dict)) and len(value) == 0:
            return self
        self[key] = value
        return self


def domain_body(domain_name: Optional[str]) -> Body:
    """The body of the many requests that only name a domain."""
    return Body(domainName=strip(domain_name))


class Query(list):
    """A query string under construction: a list of ``(key, value)`` pairs.

    Every method skips empty values, so the API sees only what the caller set.
    """

    def text(self, key: str, value: Optional[str]) -> "Query":
        value = strip(value)
        if value:
            self.append((key, value))
        return self

    def always(self, key: str, value: Any) -> "Query":
        """Add the key even when the value is empty."""
        self.append((key, "" if value is None else _plain(value)))
        return self

    def number(self, key: str, value: Optional[Union[int, float]]) -> "Query":
        if value:
            self.append((key, _plain(value)))
        return self

    def flag(self, key: str, value: Optional[bool]) -> "Query":
        if value is not None:
            self.append((key, "true" if value else "false"))
        return self

    def date(self, key: str, value: Optional[datetime]) -> "Query":
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            self.append((key, value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
        return self

    def each(self, key: str, values: Optional[Iterable[Any]]) -> "Query":
        """Add the key once per value: ``TransactionTypes=1&TransactionTypes=2``."""
        for v in non_blank([_plain(x) for x in as_list(values)]):
            self.append((key, v))
        return self

    def joined(self, key: str, values: Optional[Iterable[Any]]) -> "Query":
        """Add the values as one comma-separated value: ``StatusIds=0,7``."""
        parts = non_blank([_plain(x) for x in as_list(values)])
        if parts:
            self.append((key, ",".join(parts)))
        return self

    def page(self, skip: int = 0, limit: int = 0, sort: Optional[str] = "") -> "Query":
        return self.number("SkipCount", skip).number("MaxResultCount", limit).text("Sorting", sort)


def _plain(value: Any) -> str:
    """The query string form of a value: enums by number or API value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, enum.Enum):
        value = value.value
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def validate_paging(v: Validator, skip: int, limit: int) -> None:
    v.check(skip is None or skip >= 0, "skip", "must not be negative")
    v.check(limit is None or limit >= 0, "limit", "must not be negative")


def parse_enum(enum_cls: Any, value: Any) -> Any:
    """Parse a user value into an enum member (validation has already run)."""
    if value is None or value == "":
        return None
    return enum_cls.parse(value)


def enum_values(enum_cls: Any, values: Any) -> List[Any]:
    return [enum_cls.parse(v) for v in as_list(values) if v is not None and v != ""]
