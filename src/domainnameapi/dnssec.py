"""DS records at the registry. CLI: ``dna dnssec ...``"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, List, Optional, Union

from ._service import Service
from .enums import DNSSECAlgorithm, DNSSECOperationType, DNSSECStatus, DSDigestType, DSRecordStatus
from .model import Model, boolean, enum_list, enum_value, integer, model_list, text, timestamp
from .request import BaseRequest, Query, Safety, Validator, as_list, domain_body, strip

__all__ = [
    "DNSSECAddRequest",
    "DNSSECDisableRequest",
    "DNSSECGetRequest",
    "DNSSECInfo",
    "DNSSECOperationResult",
    "DNSSECRemoveRequest",
    "DNSSECService",
    "DS",
    "DSRecord",
]


# ---------------------------------------------------------------------------
# Models


@dataclass
class DSRecord(Model):
    """A DS record at the registry."""

    key_tag: int = integer("keyTag")
    algorithm: Optional[DNSSECAlgorithm] = enum_value("algorithm", DNSSECAlgorithm)
    digest_type: Optional[DSDigestType] = enum_value("digestType", DSDigestType)
    digest: str = text("digest")
    status: Optional[DSRecordStatus] = enum_value("status", DSRecordStatus)
    is_algorithm_not_recommended: bool = boolean("isAlgorithmNotRecommended")
    created_at: Optional[datetime] = timestamp("createdAt")
    activated_at: Optional[datetime] = timestamp("activatedAt")
    removed_at: Optional[datetime] = timestamp("removedAt")


@dataclass
class DNSSECInfo(Model):
    """The DNSSEC state of a domain."""

    domain_name: str = text("domainName")
    #: ``True`` when the TLD supports DNSSEC.
    available: bool = boolean("isDnssecAvailable")
    status: Optional[DNSSECStatus] = enum_value("status", DNSSECStatus)
    delegation_signed: bool = boolean("delegationSigned")
    max_sig_life: int = integer("maxSigLife")
    last_changed_at: Optional[datetime] = timestamp("lastChangedAt")
    ds_records: List[DSRecord] = model_list("dsRecords", DSRecord)
    allowed_algorithms: List[DNSSECAlgorithm] = enum_list("allowedAlgorithms", DNSSECAlgorithm)
    allowed_digest_types: List[DSDigestType] = enum_list("allowedDigestTypes", DSDigestType)
    max_ds_record_count: int = integer("maxDsRecordCount")


@dataclass
class DNSSECOperationResult(Model):
    """The result of one DNSSEC operation."""

    key_tag: int = integer("keyTag")
    operation_type: Optional[DNSSECOperationType] = enum_value("operationType", DNSSECOperationType)
    success: bool = boolean("isSuccess")
    #: The registry accepted the change but has not confirmed it yet.
    pending: bool = boolean("isPending")
    message: str = text("resultMessage")


@dataclass
class _OperationList(Model):
    items: List[DNSSECOperationResult] = model_list("items", DNSSECOperationResult)


@dataclass
class DS:
    """A DS record to publish or remove, as your DNS provider shows it."""

    key_tag: int
    algorithm: Union[DNSSECAlgorithm, int, str]
    digest_type: Union[DSDigestType, int, str]
    digest: str

    @classmethod
    def parse(cls, value: str) -> "DS":
        """Parse a DS record in presentation format.

        Accepts ``"2371 13 2 1F987CC6583E92DF0890718C42..."`` or a whole zone-file
        line such as ``"example.com. 3600 IN DS 2371 13 2 1F98..."``. Spaces inside
        the digest are removed. Raises :class:`ValueError`.
        """
        words = (value or "").split()
        for i, w in enumerate(words):
            if w.upper() == "DS":
                words = words[i + 1:]
                break
        error = ValueError("%r is not a DS record (want KEYTAG ALGORITHM DIGESTTYPE DIGEST)" % (value,))
        if len(words) < 4:
            raise error
        try:
            key_tag = int(words[0])
            algorithm = DNSSECAlgorithm.parse(words[1])
            digest_type = DSDigestType.parse(words[2])
        except ValueError:
            raise error from None
        return cls(key_tag, algorithm, digest_type, "".join(words[3:]).upper())

    @classmethod
    def coerce(cls, value: Union["DS", str]) -> "DS":
        return cls.parse(value) if isinstance(value, str) else value

    def __str__(self) -> str:
        return "%d %d %d %s" % (self.key_tag, self._algorithm(), self._digest_type(), self._digest())

    def _algorithm(self) -> int:
        return int(DNSSECAlgorithm.parse(self.algorithm))

    def _digest_type(self) -> int:
        return int(DSDigestType.parse(self.digest_type))

    def _digest(self) -> str:
        return "".join((self.digest or "").split()).upper()

    def to_api(self) -> dict:
        return {"keyTag": self.key_tag, "algorithm": self._algorithm(), "digestType": self._digest_type(),
                "digest": self._digest()}

    def validate(self, v: Validator, prefix: str) -> None:
        ok = isinstance(self.key_tag, int) and not isinstance(self.key_tag, bool) and 0 <= self.key_tag <= 65535
        v.check(ok, prefix + ".key_tag", "must be between 0 and 65535")
        v.enum(prefix + ".algorithm", self.algorithm, DNSSECAlgorithm, optional=False)
        v.enum(prefix + ".digest_type", self.digest_type, DSDigestType, optional=False)
        v.required(prefix + ".digest", self.digest)
        v.max_length(prefix + ".digest", self._digest(), 128)


# ---------------------------------------------------------------------------
# Requests


@dataclass
class DNSSECGetRequest(BaseRequest):
    """Read the DNSSEC state of a domain. CLI: ``dna dnssec get``"""

    method = "GET"
    path = "/api/v1/domains/dns/dnssec"
    safety = Safety.READ
    response = DNSSECInfo

    domain_name: str = ""

    def query(self) -> Query:
        return Query().text("DomainName", self.domain_name)

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)


@dataclass
class DNSSECAddRequest(BaseRequest):
    """Publish DS records at the registry. CLI: ``dna dnssec add``"""

    method = "POST"
    path = "/api/v1/domains/dns/dnssec"
    safety = Safety.WRITE
    response = _OperationList

    domain_name: str = ""
    #: :class:`DS` records, or strings :meth:`DS.parse` accepts.
    records: List[Union[DS, str]] = field(default_factory=list)

    def _records(self) -> List[DS]:
        return [DS.coerce(r) for r in as_list(self.records)]

    def body(self) -> dict:
        return {"domainName": strip(self.domain_name), "records": [r.to_api() for r in self._records()]}

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)
        records = as_list(self.records)
        v.check(len(records) > 0, "records", "needs at least one value")
        for i, r in enumerate(records):
            try:
                DS.coerce(r).validate(v, "records[%d]" % i)
            except ValueError as err:
                v.add("records[%d]" % i, str(err))


@dataclass
class DNSSECRemoveRequest(BaseRequest):
    """Remove one DS record. CLI: ``dna dnssec remove``"""

    method = "DELETE"
    path = "/api/v1/domains/dns/dnssec"
    safety = Safety.DESTRUCTIVE
    response = DNSSECOperationResult

    domain_name: str = ""
    record: Optional[Union[DS, str]] = None

    def query(self) -> Query:
        ds = DS.coerce(self.record)  # type: ignore[arg-type]
        return (Query().text("DomainName", self.domain_name).always("KeyTag", ds.key_tag)
                .always("Algorithm", ds._algorithm()).always("DigestType", ds._digest_type())
                .always("Digest", ds._digest()))

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)
        if not v.check(self.record is not None, "record", "is required"):
            return
        try:
            DS.coerce(self.record).validate(v, "record")  # type: ignore[arg-type]
        except ValueError as err:
            v.add("record", str(err))


@dataclass
class DNSSECDisableRequest(BaseRequest):
    """Remove every DS record of a domain. CLI: ``dna dnssec disable``"""

    method = "POST"
    path = "/api/v1/domains/dns/dnssec/disable"
    safety = Safety.DESTRUCTIVE
    response = DNSSECOperationResult

    domain_name: str = ""

    def body(self) -> Any:
        return domain_body(self.domain_name)

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)


# ---------------------------------------------------------------------------
# Service


class DNSSECService(Service):
    """DS records of domains. CLI: ``dna dnssec``"""

    __slots__ = ()

    def get(self, domain_name: str) -> DNSSECInfo:
        """The DNSSEC state of a domain: status, DS records and the algorithms the registry accepts."""
        return self._send(DNSSECGetRequest(domain_name))

    def add(self, domain_name: str, records: Union[DS, str, Iterable[Union[DS, str]]]
            ) -> List[DNSSECOperationResult]:
        """Publish DS records from your DNS provider (:class:`DS` objects or their text form).

        Wrong DS records make the domain unresolvable for validating resolvers:
        copy them exactly. Check ``success`` or ``pending`` of each result::

            client.dnssec.add("example.com", "2371 13 2 1F987CC6583E92DF0890718C42...")
        """
        res = self._send(DNSSECAddRequest(domain_name, as_list(records)))
        return res.items if res is not None else []

    def remove(self, domain_name: str, record: Union[DS, str]) -> DNSSECOperationResult:
        """Remove one DS record."""
        return self._operation(DNSSECRemoveRequest(domain_name, record))

    def disable(self, domain_name: str) -> DNSSECOperationResult:
        """Remove every DS record of a domain."""
        return self._operation(DNSSECDisableRequest(domain_name))

    def _operation(self, req: BaseRequest) -> DNSSECOperationResult:
        resp = self._exchange(req)
        res: DNSSECOperationResult = resp.value
        if res is None or (not res.success and not res.pending):
            raise self._failed(req, resp, "", res.message if res is not None else "")
        return res
