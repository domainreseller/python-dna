"""The DNS zone of domains on the platform nameservers. CLI: ``dna dns ...``

A record set is all records with the same name and type; it has one TTL, and
a record is identified by its value. Changes are live at once in the
platform's DNS, but resolve publicly only when the domain uses the platform
nameservers (see :meth:`DNSService.apply`).

The test environment (OTE) answers every zone call with HTTP 500, so zone
code can only be tried in production. Use a domain you do not mind changing.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Union

from ._service import Service
from .enums import RecordType
from .model import Model, boolean, integer, list_of, model_list, text, texts
from .request import BaseRequest, Query, Safety, Validator, as_list, non_blank, strip

__all__ = [
    "DEFAULT_TTL",
    "DNSAddRequest",
    "DNSApplyRequest",
    "DNSDeleteRequest",
    "DNSListRequest",
    "DNSService",
    "DNSUpdateRequest",
    "Record",
    "RecordSet",
    "ZoneApplyResult",
    "fqdn",
]

#: The TTL used when a request leaves it 0.
DEFAULT_TTL = 3600

RecordTypeLike = Union[RecordType, str]


def fqdn(domain_name: str, name: str) -> str:
    """The fully qualified form of a record name, the form the zone listing uses.

    ``fqdn("example.com", "www")`` is ``"www.example.com."``; ``""`` and ``"@"``
    give ``"example.com."``.
    """
    domain = strip(domain_name).rstrip(".").lower()
    name = strip(name).rstrip(".")
    lower = name.lower()
    if name in ("", "@") or lower == domain:
        return domain + "."
    if lower.endswith("." + domain):
        return lower + "."
    return lower + "." + domain + "."


def _normalize_type(value: RecordTypeLike) -> str:
    try:
        return RecordType.parse(value).value
    except ValueError:
        return strip(str(value))


# ---------------------------------------------------------------------------
# Models


@dataclass
class Record(Model):
    """One value of a record set."""

    content: str = text("content")
    disabled: bool = boolean("disabled")


@dataclass
class RecordSet(Model):
    """The records with one name and type."""

    #: Fully qualified with a trailing dot, e.g. ``"www.example.com."``.
    name: str = text("name")
    #: The record type as the API sends it, e.g. ``"A"`` or ``"TXT"``.
    type: str = text("type")
    ttl: int = integer("ttl")
    change_type: str = text("changeType")
    records: List[Record] = model_list("records", Record)

    @property
    def values(self) -> List[str]:
        """The contents of the set's records."""
        return [r.content for r in self.records]

    def matches(self, domain_name: str, name: str, type: RecordTypeLike) -> bool:  # noqa: A002
        """``True`` when the set has this name and type.

        ``name`` may be relative (``"www"``), the apex (``""``, ``"@"``) or fully qualified.
        """
        return (self.type.lower() == _normalize_type(type).lower()
                and self.name.rstrip(".").lower() == fqdn(domain_name, name).rstrip("."))


@dataclass
class ZoneApplyResult(Model):
    """What :meth:`DNSService.apply` did."""

    #: ``False`` when the domain already used the platform nameservers.
    name_servers_changed: bool = boolean("nameServersChanged")
    previous_name_servers: List[str] = texts("previousNameServers")
    current_name_servers: List[str] = texts("currentNameServers")
    system_name_servers: List[str] = texts("systemNameServers")


# ---------------------------------------------------------------------------
# Requests


def _record_name(name: str) -> str:
    name = strip(name)
    return "" if name == "@" else name


def _zone_struct(name: str, type_: RecordTypeLike, ttl: int, values: Iterable[str]) -> dict:
    return {"name": _record_name(name), "type": _normalize_type(type_), "ttl": ttl or DEFAULT_TTL,
            "contents": non_blank(values)}


def _validate_type(v: Validator, type_: RecordTypeLike) -> None:
    if not strip(str(type_ or "")):
        v.add("type", "is required")
        return
    try:
        RecordType.parse(type_)
    except ValueError:
        v.add("type", "%r is not a DNS record type the zone API supports" % (type_,))


def _is_ip(value: str, version: Optional[int] = None) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return version is None or ip.version == version


def _validate_record_set(v: Validator, domain_name: str, name: str, type_: RecordTypeLike, ttl: int,
                         values: Iterable[str]) -> None:
    v.required("domain_name", domain_name)
    _validate_type(v, type_)
    v.check(ttl is None or ttl >= 0, "ttl", "must not be negative")
    if ttl:
        v.between("ttl", ttl, 1, 86400)
    n = strip(name)
    v.check(n == "@" or not n.startswith("@"), "name", 'must not start with @ (use "@" alone for the apex)')
    apex = n in ("", "@") or n.rstrip(".").lower() == strip(domain_name).rstrip(".").lower()
    contents = non_blank(values)
    v.required_list("values", contents)
    kind = _normalize_type(type_)
    for c in contents:
        if kind == "CNAME":
            v.check(not _is_ip(c), "values", "a CNAME points to a host name, not an IP address (%s)" % c)
        elif kind == "MX":
            parts = c.split()
            v.check(len(parts) == 2 and parts[0].isdigit() and not _is_ip(parts[1]), "values",
                    'an MX value is "PRIORITY HOST", e.g. "10 mail.example.com" (%s)' % c)
        elif kind == "CAA":
            v.check(len(c.split()) == 3, "values", 'a CAA value has 3 parts, e.g. 0 issue "letsencrypt.org" (%s)' % c)
        elif kind == "A":
            v.check(_is_ip(c, 4), "values", "%s is not an IPv4 address" % c)
        elif kind == "AAAA":
            v.check(_is_ip(c, 6), "values", "%s is not an IPv6 address" % c)
    if kind == "CNAME":
        v.check(not apex, "name", "a CNAME cannot be at the apex; use an ALIAS record")


@dataclass
class DNSListRequest(BaseRequest):
    """List the record sets of a domain. CLI: ``dna dns list``"""

    method = "GET"
    path = "/api/v1/domains/zones"
    safety = Safety.READ
    response = list_of(RecordSet)

    domain_name: str = ""

    def query(self) -> Query:
        return Query().text("domainName", self.domain_name)

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)


@dataclass
class DNSAddRequest(BaseRequest):
    """Add values to a record set, creating the set when needed. Values already in the set stay.

    CLI: ``dna dns add``
    """

    method = "POST"
    path = "/api/v1/domains/zones"
    safety = Safety.WRITE

    domain_name: str = ""
    #: Relative (``"www"``), the apex (``""`` or ``"@"``) or fully qualified.
    name: str = ""
    type: RecordTypeLike = ""
    #: The record contents, e.g. ``"192.0.2.10"``, ``"10 mail.example.com"`` (MX) or
    #: ``'0 issue "letsencrypt.org"'`` (CAA). TXT values are quoted by the API.
    values: List[str] = field(default_factory=list)
    #: Seconds, 1 to 86400 (0 means :data:`DEFAULT_TTL`).
    ttl: int = 0

    def query(self) -> Query:
        return Query().text("domainName", self.domain_name)

    def body(self) -> dict:
        return {"zoneStruct": _zone_struct(self.name, self.type, self.ttl, as_list(self.values))}

    def validate(self, v: Validator) -> None:
        _validate_record_set(v, self.domain_name, self.name, self.type, self.ttl, as_list(self.values))


@dataclass
class DNSUpdateRequest(BaseRequest):
    """Replace every value of a record set (and its TTL); it can also rename the set.

    CLI: ``dna dns update``
    """

    method = "PUT"
    path = "/api/v1/domains/zones"
    safety = Safety.WRITE
    idempotent = True

    domain_name: str = ""
    #: The name of the existing set.
    record_name: str = ""
    type: RecordTypeLike = ""
    #: Replace all values of the set.
    values: List[str] = field(default_factory=list)
    #: The new name; empty keeps ``record_name``.
    name: str = ""
    #: Seconds, 1 to 86400 (0 means :data:`DEFAULT_TTL`).
    ttl: int = 0

    def _new_name(self) -> str:
        return self.record_name if not strip(self.name) else self.name

    def query(self) -> Query:
        return Query().text("domainName", self.domain_name).text("recordName", self.record_name)

    def body(self) -> dict:
        return {"zoneStruct": _zone_struct(self._new_name(), self.type, self.ttl, as_list(self.values))}

    def validate(self, v: Validator) -> None:
        v.required("record_name", self.record_name)
        _validate_record_set(v, self.domain_name, self._new_name(), self.type, self.ttl, as_list(self.values))


@dataclass
class DNSDeleteRequest(BaseRequest):
    """Remove one value from a record set; the set's other values stay. CLI: ``dna dns delete``"""

    method = "DELETE"
    path = "/api/v1/domains/zones"
    safety = Safety.DESTRUCTIVE

    domain_name: str = ""
    name: str = ""
    type: RecordTypeLike = ""
    #: The exact record content to remove.
    value: str = ""

    def query(self) -> Query:
        # "" is the apex, and is sent.
        return (Query().text("domainName", self.domain_name).text("RecordType", _normalize_type(self.type))
                .text("Record", self.value).always("Name", _record_name(self.name)))

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)
        _validate_type(v, self.type)
        v.required("value", self.value)


@dataclass
class DNSApplyRequest(BaseRequest):
    """Switch a domain to the platform nameservers so its zone is served. CLI: ``dna dns apply``"""

    method = "POST"
    path = "/api/v1/domains/zones/apply"
    safety = Safety.WRITE
    idempotent = True
    response = ZoneApplyResult

    domain_name: str = ""

    def query(self) -> Query:
        return Query().text("domainName", self.domain_name)

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)


# ---------------------------------------------------------------------------
# Service


class DNSService(Service):
    """Zone records of domains on the platform nameservers. CLI: ``dna dns``"""

    __slots__ = ()

    def list(self, domain_name: str) -> List[RecordSet]:
        """The record sets of a domain. A domain without a zone has none."""
        return self._send(DNSListRequest(domain_name)) or []

    def find(self, domain_name: str, name: str, type: RecordTypeLike) -> Optional[RecordSet]:  # noqa: A002
        """The record set with this name and type, or ``None``."""
        for s in self.list(domain_name):
            if s.matches(domain_name, name, type):
                return s
        return None

    def add(self, domain_name: str, name: str, type: RecordTypeLike,  # noqa: A002
            values: Union[str, Iterable[str]], *, ttl: int = 0) -> None:
        """Add values to a record set, creating it (and the zone) when needed::

            client.dns.add("example.com", "www", RecordType.A, "192.0.2.10", ttl=600)
        """
        self._send(DNSAddRequest(domain_name, name, type, as_list(values), ttl))

    def update(self, domain_name: str, record_name: str, type: RecordTypeLike,  # noqa: A002
               values: Union[str, Iterable[str]], *, name: str = "", ttl: int = 0) -> None:
        """Replace all values (and the TTL) of a record set; ``name`` renames it."""
        self._send(DNSUpdateRequest(domain_name, record_name, type, as_list(values), name, ttl))

    def delete(self, domain_name: str, name: str, type: RecordTypeLike, value: str) -> None:  # noqa: A002
        """Remove one value from a record set."""
        self._send(DNSDeleteRequest(domain_name, name, type, value))

    def apply(self, domain_name: str) -> ZoneApplyResult:
        """Switch the domain to the platform nameservers, so the records managed here go live.

        This replaces any other DNS provider of the domain. It does nothing
        when the domain already uses them.
        """
        return self._send(DNSApplyRequest(domain_name))
