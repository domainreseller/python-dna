"""Search, register, renew, transfer and manage domains. CLI: ``dna domain ...``"""

from __future__ import annotations

import base64
import ipaddress
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, Iterator, List, Optional, Union
from urllib.parse import urlsplit

from ._service import Service, first_text
from .contacts import Contact, ContactHandles, DomainContacts
from .enums import (
    ContactType,
    DNSSECMode,
    DocumentOperationType,
    DocumentStatus,
    DocumentType,
    DomainStatus,
    ForwardType,
    IPVersion,
)
from .errors import APIError, ErrorCode, FieldError, InputError
from .model import (
    Model,
    Page,
    attributes,
    boolean,
    enum_value,
    integer,
    model,
    model_list,
    number,
    page_of,
    paginate,
    text,
    texts,
    timestamp,
)
from .request import (
    BaseRequest,
    Body,
    Query,
    Safety,
    Validator,
    as_list,
    domain_body,
    enum_values,
    non_blank,
    parse_enum,
    strip,
    validate_paging,
)

__all__ = [
    "MAX_BULK_SEARCH",
    "MAX_DOCUMENT_SIZE",
    "MAX_DOCUMENT_UPLOAD_SIZE",
    "AuthCode",
    "Availability",
    "Document",
    "DocumentUpload",
    "DocumentUploadResult",
    "Domain",
    "DomainBulkSearchRequest",
    "DomainBulkSearchResult",
    "DomainContactsSetHandlesRequest",
    "DomainContactsUpdateRequest",
    "DomainDocumentsListRequest",
    "DomainDocumentsUploadRequest",
    "DomainForwardDeleteRequest",
    "DomainForwardGetRequest",
    "DomainForwardSetRequest",
    "DomainHostAddRequest",
    "DomainHostDeleteRequest",
    "DomainHostUpdateRequest",
    "DomainInfo",
    "DomainInfoRequest",
    "DomainListRequest",
    "DomainLockRequest",
    "DomainNameServersSetRequest",
    "DomainOperationResult",
    "DomainPrivacyRequest",
    "DomainRegisterRequest",
    "DomainRegisterWithContactsRequest",
    "DomainRenewCheckRequest",
    "DomainRenewRequest",
    "DomainRestoreRequest",
    "DomainSearchRequest",
    "DomainSearchResult",
    "DomainService",
    "DomainTransferCheckRequest",
    "DomainTransferRequest",
    "DomainTransferStatusRequest",
    "DomainUnlockRequest",
    "DomainUpdateAuthCodeRequest",
    "Forwarding",
    "Host",
    "IPAddress",
    "NameServer",
    "RenewCheck",
    "TransferCheck",
    "TransferStatus",
    "UploadedDocument",
]

#: The number of domains one :class:`DomainBulkSearchRequest` may check.
#: ``domains.bulk_search`` splits longer lists for you.
MAX_BULK_SEARCH = 30
#: Bytes per uploaded document.
MAX_DOCUMENT_SIZE = 10 << 20
#: Bytes per upload request.
MAX_DOCUMENT_UPLOAD_SIZE = 50 << 20

#: Accepted document formats. The extension must match the file's real format.
DOCUMENT_EXTENSIONS = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".odt"})

# ---------------------------------------------------------------------------
# Models


@dataclass
class Availability(Model):
    """The result of a domain search."""

    domain_name: str = text("domainName")
    tld: str = text("tld")
    #: The registry answer: ``"AVAILABLE"``, ``"NOTAVAILABLE"``, ... Test it with :attr:`available`.
    status: str = text("status")
    #: Explains a status other than AVAILABLE, e.g. ``"Domain exists"``.
    reason: str = text("reason")
    price: float = number("price")
    currency: str = text("currency")
    period: int = integer("period")
    is_premium: bool = boolean("isPremium")
    #: The registry asks for documents (``domains.upload_documents``).
    is_document_required: bool = boolean("isDocumentRequired")

    @property
    def available(self) -> bool:
        """``True`` when the domain can be registered."""
        return self.status.strip().upper() == "AVAILABLE"


@dataclass
class DomainSearchResult(Model):
    """The API's answer to :class:`DomainSearchRequest`."""

    success: bool = boolean("success")
    code: str = text("code")
    message: str = text("operationMessage")
    reason: str = text("reason")
    info: Availability = model("info", Availability)


@dataclass
class DomainBulkSearchResult(Model):
    """The API's answer to :class:`DomainBulkSearchRequest`."""

    success: bool = boolean("success")
    code: str = text("code")
    message: str = text("operationMessage")
    reason: str = text("reason")
    infos: List[Availability] = model_list("infos", Availability)


@dataclass
class NameServer(Model):
    """A nameserver of a domain in the domain list."""

    name: str = text("name")
    is_child_name_server: bool = boolean("isChildnameServer")
    is_glue_record: bool = boolean("isGlueRecord")
    is_linked: bool = boolean("isLinked")


@dataclass
class Domain(Model):
    """A domain in the domain list. ``domains.info`` returns more."""

    domain_name: str = text("domainName")
    domain_name_idn: str = text("domainNameIdn")
    is_idn: bool = boolean("isIdnName")
    status: Optional[DomainStatus] = enum_value("status", DomainStatus)
    #: The registry (EPP) status, e.g. ``"clientTransferProhibited"``.
    status_code: str = text("statusCode")
    start_date: Optional[datetime] = timestamp("startDate")
    expiration_date: Optional[datetime] = timestamp("expirationDate")
    transfer_date: Optional[datetime] = timestamp("transferDate")
    updated_date: Optional[datetime] = timestamp("updatedDate")
    #: The end of the redemption grace period.
    rgp_expiration_date: Optional[datetime] = timestamp("rgpExpirationDate")
    #: The end of the add grace period.
    agp_expiration_date: Optional[datetime] = timestamp("agpExpirationDate")
    failure_date: Optional[datetime] = timestamp("failureDate")
    finalization_date: Optional[datetime] = timestamp("finalizationDate")
    remaining_days: int = integer("remainingDay")
    locked: bool = boolean("lockStatus")
    privacy_protection: bool = boolean("privacyProtectionStatus")
    renewal_mode: str = text("renewalMode")
    object_class: str = text("objectClass")
    #: The handle of each contact role, e.g. ``{"Registrant": "DNA-1", ...}``.
    contacts: Dict[str, str] = attributes("contacts")
    name_servers: List[NameServer] = model_list("nameservers", NameServer)


@dataclass
class IPAddress(Model):
    """An address of a child nameserver."""

    address: str = text("ipAddress")
    version: Optional[IPVersion] = enum_value("ipVersion", IPVersion)


@dataclass
class Host(Model):
    """A child nameserver (glue record) such as ns1.example.com."""

    name: str = text("name")
    ip_addresses: List[IPAddress] = model_list("ipAddresses", IPAddress)


@dataclass
class DomainInfo(Model):
    """The full record of a domain."""

    domain_name: str = text("domainName")
    domain_name_idn: str = text("domainNameIdn")
    is_idn: bool = boolean("isIdnName")
    status: Optional[DomainStatus] = enum_value("status", DomainStatus)
    #: The registry (EPP) status, e.g. ``"clientTransferProhibited"``.
    status_code: str = text("statusCode")
    #: Explains the status, e.g. ``"RddsVerificationPending"``.
    status_reason: str = text("statusReason")
    #: The registry's redemption grace period status.
    rgp_status: str = text("rgpStatues")
    start_date: Optional[datetime] = timestamp("startDate")
    expiration_date: Optional[datetime] = timestamp("expirationDate")
    transfer_date: Optional[datetime] = timestamp("transferDate")
    updated_date: Optional[datetime] = timestamp("updatedDate")
    remaining_days: int = integer("remainingDay")
    reseller_id: str = text("resellerId")
    renewal_mode: str = text("renewalMode")
    #: The transfer authorization (EPP) code.
    auth_code: str = text("authCode")
    locked: bool = boolean("lockStatus")
    privacy_protection: bool = boolean("privacyProtectionStatus")
    object_id: str = text("objectId")
    is_forwarded: bool = boolean("isForwarded")
    use_trustee_contact: bool = boolean("useTrusteeContact")
    name_servers: List[str] = texts("nameservers")
    #: The child nameservers registered under the domain.
    hosts: List[Host] = model_list("hosts", Host)
    contacts: List[Contact] = model_list("contacts", Contact)
    additional_attributes: Dict[str, str] = attributes("additionalAttributes")

    def contact(self, role: Union[ContactType, str]) -> Optional[Contact]:
        """The contact in a role (``ContactType.REGISTRANT`` or ``"registrant"``), or ``None``."""
        wanted = ContactType.parse(role)
        for c in self.contacts:
            if c.type == wanted:
                return c
        return None


@dataclass
class DomainOperationResult(Model):
    """The API's answer to a registration, renewal or transfer."""

    success: bool = boolean("success")
    message: str = text("message")
    #: Identifies the domain on the platform.
    domain_id: str = text("domainId")
    #: The domain's status after the operation, e.g. ``"Active"`` or a waiting status.
    status: str = text("status")
    expiration_date: Optional[datetime] = timestamp("expirationDate")


@dataclass
class RenewCheck(Model):
    """Whether and at what price a domain can be renewed."""

    renewable: bool = boolean("renewabilityStatus")
    renewal_lock: bool = boolean("renewalLock")
    error_message_key: str = text("errorMessageKey")
    is_premium: bool = boolean("isPremium")
    premium_price: float = number("premiumPrice")
    premium_currency: str = text("premiumCurrency")


@dataclass
class TransferCheck(Model):
    """Whether a domain can be transferred in."""

    #: The overall answer.
    transferable: bool = boolean("transferAvailabilityStatus")
    message_key: str = text("messageKey")
    message: str = text("message")
    auth_code_required: bool = boolean("authCodeIsRequired")
    auth_code_valid: bool = boolean("authCodeIsValid")
    user_transfer_required: bool = boolean("userTransferRequired")
    #: The losing registrar still locks the domain.
    transfer_lock: bool = boolean("transferLock")
    domain_statuses: List[str] = texts("domainStatuses")
    additional_attributes: Dict[str, str] = attributes("additionalAttributes")
    is_premium: bool = boolean("isPremium")
    premium_price: float = number("premiumPrice")
    premium_currency: str = text("premiumCurrency")


@dataclass
class TransferStatus(Model):
    """The state of a pending incoming transfer."""

    domain_name: str = text("domainName")
    status: str = text("status")
    requested_date: str = text("requestedDate")
    final_date: str = text("finalDate")
    requested_client_id: str = text("requestedClientId")
    action_client_id: str = text("actionClientId")


@dataclass
class AuthCode(Model):
    """A domain's transfer authorization (EPP) code."""

    domain_name: str = text("domainName")
    auth_code: str = text("authCode")


@dataclass
class Document(Model):
    """A registry document of a domain."""

    name: str = text("name")
    type: Optional[DocumentType] = enum_value("type", DocumentType)
    status: Optional[DocumentStatus] = enum_value("status", DocumentStatus)
    operation_type: Optional[DocumentOperationType] = enum_value("operationType", DocumentOperationType)
    uploaded_date: Optional[datetime] = timestamp("uploadedDate")


@dataclass
class UploadedDocument(Model):
    """A document the API stored."""

    name: str = text("name")
    size: int = integer("size")
    mime_type: str = text("mimeType")
    type: Optional[DocumentType] = enum_value("type", DocumentType)
    uploaded_date: Optional[datetime] = timestamp("uploadedDate")


@dataclass
class DocumentUploadResult(Model):
    """The API's answer to an upload."""

    uploaded: List[UploadedDocument] = model_list("uploaded", UploadedDocument)
    #: File names that were already stored.
    duplicates: List[str] = texts("duplicates")
    #: File names that could not be stored.
    failed: List[str] = texts("failed")
    total_document_count: int = integer("totalDocumentCount")
    total_document_size: int = integer("totalDocumentSize")


@dataclass
class DocumentUpload:
    """A file to upload as a registry document. ``content`` is base64-encoded for you."""

    type: Union[DocumentType, int, str]
    #: Must end in .pdf, .jpg, .jpeg, .png, .doc, .docx or .odt.
    file_name: str
    #: The file content (at most 10 MB).
    content: bytes

    @classmethod
    def from_file(cls, document_type: Union[DocumentType, int, str], path: Union[str, "os.PathLike[str]"]
                  ) -> "DocumentUpload":
        """Read a file into a :class:`DocumentUpload`."""
        with open(path, "rb") as fh:
            content = fh.read()
        return cls(document_type, os.path.basename(os.fspath(path)), content)


@dataclass
class Forwarding(Model):
    """The URL forwarding of a domain."""

    #: The target address.
    url: str = text("redirectAlias")
    type: Optional[ForwardType] = enum_value("redirectType", ForwardType)


# ---------------------------------------------------------------------------
# Search, list, info


def _require_domain(v: Validator, domain_name: str) -> None:
    v.required("domain_name", domain_name)


@dataclass
class DomainSearchRequest(BaseRequest):
    """Check the availability and price of a domain. CLI: ``dna domain search``"""

    method = "POST"
    path = "/api/v1/domains/search"
    safety = Safety.READ
    response = DomainSearchResult

    domain_name: str = ""
    #: The price currency, e.g. ``"USD"`` or ``"TRY"``. Empty uses the account's.
    currency: str = ""

    def body(self) -> Body:
        return domain_body(self.domain_name).set("currency", self.currency)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)


@dataclass
class DomainBulkSearchRequest(BaseRequest):
    """Check several domains at once (at most 30). CLI: ``dna domain bulk-search``"""

    method = "POST"
    path = "/api/v1/domains/bulk-search"
    safety = Safety.READ
    response = DomainBulkSearchResult

    domain_names: List[str] = field(default_factory=list)
    #: The price currency, e.g. ``"USD"`` or ``"TRY"``. Empty uses the account's.
    currency: str = ""

    def body(self) -> List[Body]:
        return [domain_body(name).set("currency", self.currency) for name in non_blank(self.domain_names)]

    def validate(self, v: Validator) -> None:
        n = len(non_blank(self.domain_names))
        v.required_list("domain_names", self.domain_names)
        v.check(n <= MAX_BULK_SEARCH, "domain_names",
                "may hold at most %d domains; domains.bulk_search splits longer lists" % MAX_BULK_SEARCH)


@dataclass
class DomainListRequest(BaseRequest):
    """List your domains. CLI: ``dna domain list``"""

    method = "GET"
    path = "/api/v1/domains"
    safety = Safety.READ
    response = page_of(Domain)

    #: Keep domains whose name contains this text.
    domain_name: str = ""
    #: Keep only domains in these states.
    statuses: Optional[List[Any]] = None
    skip: int = 0
    limit: int = 0
    #: A sort expression such as ``"expirationDate desc"``.
    sort: str = ""

    def query(self) -> Query:
        statuses = [int(s) for s in enum_values(DomainStatus, self.statuses)]
        return Query().text("DomainName", self.domain_name).joined("StatusIds", statuses).page(
            self.skip, self.limit, self.sort)

    def validate(self, v: Validator) -> None:
        validate_paging(v, self.skip, self.limit)
        for s in as_list(self.statuses):
            v.enum("statuses", s, DomainStatus)


@dataclass
class DomainInfoRequest(BaseRequest):
    """Read the full record of a domain. CLI: ``dna domain info``"""

    method = "GET"
    path = "/api/v1/domains/info"
    safety = Safety.READ
    response = DomainInfo

    domain_name: str = ""

    def query(self) -> Query:
        return Query().text("DomainName", self.domain_name)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)


# ---------------------------------------------------------------------------
# Register, renew, restore


@dataclass
class DomainRegisterRequest(BaseRequest):
    """Register a domain with existing contact handles. **Charges your balance.**

    CLI: ``dna domain register``
    """

    method = "POST"
    path = "/api/v1/domains/register"
    safety = Safety.BILLABLE
    response = DomainOperationResult

    domain_name: str = ""
    #: The contact handles of the four roles; a single handle string is used for all four.
    handles: Union[ContactHandles, str, None] = None
    #: The nameserver host names; most registries want two or more.
    name_servers: List[str] = field(default_factory=list)
    #: The registration period, 1 to 10 years.
    years: int = 1
    #: The registry attributes some TLDs require (see ``products.tld(...).required_attributes``).
    tld_attributes: Optional[Dict[str, str]] = None

    def body(self) -> Body:
        return (domain_body(self.domain_name)
                .set("period", self.years)
                .set("nameServers", non_blank(self.name_servers))
                .set("handles", ContactHandles.coerce(self.handles).to_api())
                .set("tldAttributes", _string_map(self.tld_attributes)))

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        v.between("years", self.years, 1, 10)
        v.required_list("name_servers", self.name_servers)
        ContactHandles.coerce(self.handles).validate(v, "handles", require_all=True)


@dataclass
class DomainRegisterWithContactsRequest(BaseRequest):
    """Register a domain with the contact details given inline. **Charges your balance.**

    CLI: ``dna domain register-with-contacts``
    """

    method = "POST"
    path = "/api/v1/domains/register-with-contacts"
    safety = Safety.BILLABLE
    response = DomainOperationResult

    domain_name: str = ""
    #: The contacts of the four roles; a single :class:`Contact` is used for all four.
    #: Required unless ``use_trustee_contact`` is set.
    contacts: Union[DomainContacts, Contact, None] = None
    name_servers: List[str] = field(default_factory=list)
    #: The registration period, 1 to 10 years.
    years: int = 1
    tld_attributes: Optional[Dict[str, str]] = None
    #: Use the registrar's trustee contact, for TLDs with ``TLD.is_support_trustee``.
    use_trustee_contact: bool = False

    def body(self) -> Body:
        b = (domain_body(self.domain_name)
             .set("period", self.years)
             .set("nameServers", non_blank(self.name_servers))
             .set("tldAttributes", _string_map(self.tld_attributes)))
        contacts = DomainContacts.coerce(self.contacts).to_api()
        if contacts:
            b["contacts"] = contacts
        if self.use_trustee_contact:
            b["useTrusteeContact"] = True
        return b

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        v.between("years", self.years, 1, 10)
        v.required_list("name_servers", self.name_servers)
        contacts = DomainContacts.coerce(self.contacts)
        if not self.use_trustee_contact or contacts.to_api():
            contacts.validate(v, "contacts", require_all=not self.use_trustee_contact)


@dataclass
class DomainRenewRequest(BaseRequest):
    """Renew a domain. **Charges your balance.** CLI: ``dna domain renew``"""

    method = "POST"
    path = "/api/v1/domains/renew"
    safety = Safety.BILLABLE
    response = DomainOperationResult

    domain_name: str = ""
    #: Years to add, 1 to 10.
    years: int = 0

    def body(self) -> Body:
        return domain_body(self.domain_name).set("period", self.years)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        v.between("years", self.years, 1, 10, optional=False)


@dataclass
class DomainRenewCheckRequest(BaseRequest):
    """Check whether a domain can be renewed. CLI: ``dna domain renew-check``"""

    method = "POST"
    path = "/api/v1/domains/renew/check"
    safety = Safety.READ
    response = RenewCheck

    domain_name: str = ""
    #: Years to add, 1 to 10 (0 lets the API choose).
    years: int = 0

    def body(self) -> Body:
        return domain_body(self.domain_name).set("period", self.years)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        v.between("years", self.years, 1, 10)


@dataclass
class DomainRestoreRequest(BaseRequest):
    """Restore a deleted domain during the redemption period (``DomainStatus.PENDING_DELETE``).

    **Charges your balance**; restore fees are usually high. CLI: ``dna domain restore``
    """

    method = "POST"
    path = "/api/v1/domains/restore"
    safety = Safety.BILLABLE

    domain_name: str = ""

    def body(self) -> Body:
        return domain_body(self.domain_name)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)


# ---------------------------------------------------------------------------
# Transfers


@dataclass
class DomainTransferRequest(BaseRequest):
    """Start an incoming transfer. **Charges your balance.** CLI: ``dna domain transfer``"""

    method = "POST"
    path = "/api/v1/domains/transfer"
    safety = Safety.BILLABLE
    response = DomainOperationResult

    domain_name: str = ""
    #: The transfer authorization (EPP) code from the current registrar. Sent as given:
    #: surrounding spaces can be part of it.
    auth_code: str = ""
    #: Years added on transfer, 1 to 10 (0 lets the registry decide; usually 1).
    years: int = 0

    def body(self) -> Body:
        b = domain_body(self.domain_name).set("period", self.years)
        if self.auth_code:
            b["authCode"] = self.auth_code
        return b

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        v.between("years", self.years, 1, 10)


@dataclass
class DomainTransferCheckRequest(BaseRequest):
    """Check whether a domain can be transferred in with an auth code.

    CLI: ``dna domain transfer-check``
    """

    method = "POST"
    path = "/api/v1/domains/transfers/check"
    safety = Safety.READ
    response = TransferCheck

    domain_name: str = ""
    auth_code: str = ""

    def body(self) -> Dict[str, Any]:
        return {"domainName": strip(self.domain_name), "authCode": self.auth_code}

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        v.required("auth_code", self.auth_code)


@dataclass
class DomainTransferStatusRequest(BaseRequest):
    """Read the state of a pending transfer. CLI: ``dna domain transfer-status``"""

    method = "POST"
    path = "/api/v1/domains/transfers/query"
    safety = Safety.READ
    response = TransferStatus

    domain_name: str = ""

    def body(self) -> Body:
        return domain_body(self.domain_name)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)


# ---------------------------------------------------------------------------
# Settings: lock, privacy, auth code, nameservers, child nameservers


@dataclass
class DomainLockRequest(BaseRequest):
    """Turn the transfer lock on. CLI: ``dna domain lock``"""

    method = "POST"
    path = "/api/v1/domains/lock"
    safety = Safety.WRITE
    idempotent = True

    domain_name: str = ""

    def body(self) -> Body:
        return domain_body(self.domain_name)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)


@dataclass
class DomainUnlockRequest(BaseRequest):
    """Turn the transfer lock off, which a transfer to another registrar needs.

    CLI: ``dna domain unlock``
    """

    method = "POST"
    path = "/api/v1/domains/unlock"
    safety = Safety.WRITE
    idempotent = True

    domain_name: str = ""

    def body(self) -> Body:
        return domain_body(self.domain_name)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)


@dataclass
class DomainPrivacyRequest(BaseRequest):
    """Turn WHOIS privacy protection on or off. CLI: ``dna domain privacy``"""

    method = "POST"
    path = "/api/v1/domains/privacy"
    safety = Safety.WRITE
    idempotent = True

    domain_name: str = ""
    enabled: bool = False

    def body(self) -> Dict[str, Any]:
        return {"domainName": strip(self.domain_name), "privacyStatus": bool(self.enabled)}

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)


@dataclass
class DomainUpdateAuthCodeRequest(BaseRequest):
    """Ask the registry for a new transfer auth code. CLI: ``dna domain update-auth-code``"""

    method = "PUT"
    path = "/api/v1/domains/auth"
    safety = Safety.WRITE
    response = AuthCode

    domain_name: str = ""

    def body(self) -> Body:
        return domain_body(self.domain_name)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)


@dataclass
class DomainNameServersSetRequest(BaseRequest):
    """Replace the nameservers of a domain. CLI: ``dna domain nameservers set``"""

    method = "PUT"
    path = "/api/v1/domains/dns/name-server"
    safety = Safety.WRITE
    idempotent = True

    domain_name: str = ""
    #: The complete new list of nameserver host names.
    name_servers: List[str] = field(default_factory=list)
    #: Matters only for a DNSSEC-signed domain. ``DNSSECMode.BLOCK`` (the default)
    #: refuses the change while DS records exist.
    dnssec_mode: Union[DNSSECMode, int, str] = DNSSECMode.BLOCK

    def body(self) -> Dict[str, Any]:
        return {
            "domainName": strip(self.domain_name),
            "nameServers": [ns.lower() for ns in non_blank(self.name_servers)],
            "dnssecMode": int(parse_enum(DNSSECMode, self.dnssec_mode) or DNSSECMode.BLOCK),
        }

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        v.required_list("name_servers", self.name_servers)
        v.enum("dnssec_mode", self.dnssec_mode, DNSSECMode)


def _ip_addresses(values: Any) -> List[Dict[str, str]]:
    out = []
    for s in non_blank(values):
        try:
            version = IPVersion.V4 if ipaddress.ip_address(s).version == 4 else IPVersion.V6
        except ValueError:
            version = IPVersion.V6
        out.append({"ipAddress": s, "ipVersion": version.value})
    return out


def _validate_ips(v: Validator, values: Any) -> None:
    v.required_list("ip_addresses", values)
    for s in non_blank(values):
        try:
            ipaddress.ip_address(s)
        except ValueError:
            v.add("ip_addresses", "%s is not an IP address" % s)


@dataclass
class DomainHostAddRequest(BaseRequest):
    """Create a child nameserver (glue record) such as ns1.example.com.

    CLI: ``dna domain host add``
    """

    method = "POST"
    path = "/api/v1/domains/dns/host"
    safety = Safety.WRITE

    domain_name: str = ""
    #: The full host name, e.g. ``"ns1.example.com"``.
    host_name: str = ""
    #: IPv4 or IPv6 addresses; the version is detected.
    ip_addresses: List[str] = field(default_factory=list)

    def body(self) -> Dict[str, Any]:
        return {"domainName": strip(self.domain_name), "hostName": strip(self.host_name),
                "ipAddresses": _ip_addresses(self.ip_addresses)}

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        v.required("host_name", self.host_name)
        _validate_ips(v, self.ip_addresses)


@dataclass
class DomainHostUpdateRequest(BaseRequest):
    """Change a child nameserver's IP addresses, and optionally its name.

    CLI: ``dna domain host update``
    """

    method = "PUT"
    path = "/api/v1/domains/dns/host"
    safety = Safety.WRITE
    idempotent = True

    domain_name: str = ""
    host_name: str = ""
    #: The complete new list of addresses.
    ip_addresses: List[str] = field(default_factory=list)
    #: Renames the host; leave it empty to keep the name.
    new_host_name: str = ""

    def body(self) -> Body:
        return Body(domainName=strip(self.domain_name), hostName=strip(self.host_name),
                    ipAddresses=_ip_addresses(self.ip_addresses)).set("newHostName", self.new_host_name)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        v.required("host_name", self.host_name)
        _validate_ips(v, self.ip_addresses)


@dataclass
class DomainHostDeleteRequest(BaseRequest):
    """Delete a child nameserver. CLI: ``dna domain host delete``"""

    method = "DELETE"
    path = "/api/v1/domains/dns/host"
    safety = Safety.DESTRUCTIVE

    domain_name: str = ""
    host_name: str = ""

    def query(self) -> Query:
        return Query().text("DomainName", self.domain_name).text("HostName", self.host_name)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        v.required("host_name", self.host_name)


# ---------------------------------------------------------------------------
# Contacts of a domain


@dataclass
class DomainContactsUpdateRequest(BaseRequest):
    """Replace contacts of a domain with inline details. Roles left ``None`` stay as they are.

    Changing the registrant may start an owner-change process, with documents
    on some TLDs. CLI: ``dna domain contacts update``
    """

    method = "PUT"
    path = "/api/v1/domains/contacts/update"
    safety = Safety.WRITE

    domain_name: str = ""
    contacts: DomainContacts = field(default_factory=DomainContacts)

    def body(self) -> Dict[str, Any]:
        return {"domainName": strip(self.domain_name), "contacts": DomainContacts.coerce(self.contacts).to_api()}

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        DomainContacts.coerce(self.contacts).validate(v, "contacts", require_all=False)


@dataclass
class DomainContactsSetHandlesRequest(BaseRequest):
    """Point contact roles of a domain at existing handles. Roles left empty stay as they are.

    CLI: ``dna domain contacts set-handles``
    """

    method = "PUT"
    path = "/api/v1/domains/contacts/update-with-handle"
    safety = Safety.WRITE

    domain_name: str = ""
    handles: Union[ContactHandles, str] = field(default_factory=ContactHandles)

    def body(self) -> Dict[str, Any]:
        return {"domainName": strip(self.domain_name), "handleItems": ContactHandles.coerce(self.handles).to_api()}

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        ContactHandles.coerce(self.handles).validate(v, "handles", require_all=False)


# ---------------------------------------------------------------------------
# Registry documents


@dataclass
class DomainDocumentsListRequest(BaseRequest):
    """List the registry documents of a domain. CLI: ``dna domain documents list``"""

    method = "GET"
    path = "/api/v1/domains/documents"
    safety = Safety.READ
    response = page_of(Document)

    domain_name: str = ""
    #: Keep only these document types.
    types: Optional[List[Any]] = None
    skip: int = 0
    limit: int = 0
    sort: str = ""

    def query(self) -> Query:
        types = [int(t) for t in enum_values(DocumentType, self.types)]
        return Query().text("DomainName", self.domain_name).joined("DocumentTypes", types).page(
            self.skip, self.limit, self.sort)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        validate_paging(v, self.skip, self.limit)
        for t in as_list(self.types):
            v.enum("types", t, DocumentType)


@dataclass
class DomainDocumentsUploadRequest(BaseRequest):
    """Upload the documents a registry asked for (``DomainStatus.WAITING_FOR_DOCUMENT``).

    CLI: ``dna domain documents upload``
    """

    method = "POST"
    path = "/api/v1/domains/documents"
    safety = Safety.WRITE
    response = DocumentUploadResult

    domain_name: str = ""
    documents: List[DocumentUpload] = field(default_factory=list)

    def body(self) -> Dict[str, Any]:
        return {
            "domainName": strip(self.domain_name),
            "documents": [{
                "documentType": int(DocumentType.parse(d.type)),
                "fileName": strip(d.file_name),
                "fileContent": base64.b64encode(bytes(d.content or b"")).decode("ascii"),
            } for d in as_list(self.documents)],
        }

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        docs = as_list(self.documents)
        v.check(len(docs) > 0, "documents", "needs at least one value")
        total = 0
        for i, d in enumerate(docs):
            f = "documents[%d]" % i
            v.enum(f + ".type", d.type, DocumentType, optional=False)
            v.required(f + ".file_name", d.file_name)
            ext = os.path.splitext(strip(d.file_name))[1].lower()
            v.check(not d.file_name or ext in DOCUMENT_EXTENSIONS, f + ".file_name",
                    "must be a PDF, JPG, JPEG, PNG, DOC, DOCX or ODT file")
            size = len(d.content or b"")
            v.check(size > 0, f + ".content", "is empty")
            v.check(size <= MAX_DOCUMENT_SIZE, f + ".content", "is larger than 10 MB")
            total += size
        v.check(total <= MAX_DOCUMENT_UPLOAD_SIZE, "documents",
                "are larger than 50 MB together; upload them in several requests")


# ---------------------------------------------------------------------------
# URL forwarding


@dataclass
class DomainForwardGetRequest(BaseRequest):
    """Read the URL forwarding of a domain. CLI: ``dna domain forward get``"""

    method = "GET"
    path = "/api/v1/domains/forwards"
    safety = Safety.READ
    response = Forwarding

    domain_name: str = ""

    def query(self) -> Query:
        return Query().text("domainName", self.domain_name)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)


@dataclass
class DomainForwardSetRequest(BaseRequest):
    """Forward a domain to a URL. CLI: ``dna domain forward set``"""

    method = "POST"
    path = "/api/v1/domains/forwards"
    safety = Safety.WRITE
    idempotent = True

    domain_name: str = ""
    #: The target, e.g. ``"https://www.example.org"``.
    url: str = ""
    #: ``ForwardType.STANDARD`` (a 301 redirect, the default) or ``ForwardType.FRAME``.
    type: Union[ForwardType, str] = ForwardType.STANDARD

    def body(self) -> Dict[str, Any]:
        kind = ForwardType.parse(self.type or ForwardType.STANDARD)
        return {"domainName": strip(self.domain_name), "redirectAddress": strip(self.url), "forwardType": kind.value}

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)
        if v.required("url", self.url):
            parts = urlsplit(strip(self.url))
            v.check(parts.scheme in ("http", "https") and parts.netloc, "url", "must be an http:// or https:// URL")
        if self.type:
            try:
                ForwardType.parse(self.type)
            except ValueError as err:
                v.add("type", str(err))


@dataclass
class DomainForwardDeleteRequest(BaseRequest):
    """Remove the URL forwarding of a domain. CLI: ``dna domain forward delete``"""

    method = "DELETE"
    path = "/api/v1/domains/forwards"
    safety = Safety.DESTRUCTIVE

    domain_name: str = ""

    def query(self) -> Query:
        return Query().text("DomainName", self.domain_name)

    def validate(self, v: Validator) -> None:
        _require_domain(v, self.domain_name)


def _string_map(values: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not values:
        return {}
    out = {}
    for k, v in values.items():
        if isinstance(v, bool):
            v = "true" if v else "false"
        out[str(k)] = "" if v is None else str(v)
    return out


# ---------------------------------------------------------------------------
# Service


class DomainService(Service):
    """Search, register, renew, transfer and manage domains. CLI: ``dna domain``"""

    __slots__ = ()

    # -- search, list, info ---------------------------------------------------

    def search(self, domain_name: str, *, currency: Optional[str] = None) -> Availability:
        """Whether a domain is available and what it costs.

        Prices use ``currency``, the client's currency or the account's. The API
        allows 2 searches per second; the client paces them::

            a = client.domains.search("example.com")
            if a.available:
                print(a.price, a.currency)
        """
        req = DomainSearchRequest(domain_name, currency if currency is not None else self._client.currency)
        resp = self._exchange(req)
        res: DomainSearchResult = resp.value
        if not res.success:
            raise self._failed(req, resp, res.code, first_text(res.reason, res.message))
        return res.info

    def bulk_search(self, domain_names: Iterable[str], *, currency: Optional[str] = None) -> List[Availability]:
        """Check several domains; each result has its own status.

        Lists longer than 30 are sent in several requests.
        """
        names = non_blank(domain_names)
        if not names:
            raise InputError("DomainBulkSearchRequest", [FieldError("domain_names", "needs at least one value")])
        cur = currency if currency is not None else self._client.currency
        out: List[Availability] = []
        for start in range(0, len(names), MAX_BULK_SEARCH):
            req = DomainBulkSearchRequest(names[start:start + MAX_BULK_SEARCH], cur)
            resp = self._exchange(req)
            res: DomainBulkSearchResult = resp.value
            if not res.success and not res.infos:
                raise self._failed(req, resp, res.code, first_text(res.reason, res.message))
            out.extend(res.infos)
        return out

    def list(self, *, domain_name: str = "", statuses: Optional[Iterable[Any]] = None, skip: int = 0,
             limit: int = 0, sort: str = "") -> Page[Domain]:
        """One page of your domains."""
        return self._send(DomainListRequest(domain_name, as_list(statuses) or None, skip, limit, sort))

    def all(self, *, domain_name: str = "", statuses: Optional[Iterable[Any]] = None, sort: str = "",
            page_size: int = 100) -> Iterator[Domain]:
        """Every matching domain; pages are fetched as you iterate::

            for d in client.domains.all(statuses=[DomainStatus.ACTIVE]):
                if d.remaining_days < 30:
                    print(d.domain_name, "expires", d.expiration_date)
        """
        status_list = as_list(statuses) or None
        return paginate(lambda skip, limit: self.list(domain_name=domain_name, statuses=status_list, skip=skip,
                                                      limit=limit, sort=sort), 0, page_size)

    def info(self, domain_name: str) -> DomainInfo:
        """The full record of a domain: dates, status, lock and privacy, nameservers,
        child hosts, contacts and the auth code. Not rate limited."""
        return self._send(DomainInfoRequest(domain_name))

    # -- register, renew, restore -------------------------------------------------

    def register(self, domain_name: str, *, handles: Union[ContactHandles, str],
                 name_servers: Iterable[str], years: int = 1,
                 tld_attributes: Optional[Dict[str, str]] = None) -> DomainOperationResult:
        """Register a domain with existing contact handles. **Charges your balance.**

        ``handles`` is a :class:`ContactHandles`, or one handle for all four
        roles. Check availability and price with :meth:`search` first. A
        refusal (the domain is taken, a rule failed) raises
        :class:`~domainnameapi.OperationError`; after a network error, check
        ``err.outcome_unknown`` and the domain's state before trying again.
        """
        return self._operation(DomainRegisterRequest(domain_name, handles, list(non_blank(name_servers)), years,
                                                     tld_attributes))

    def register_with_contacts(self, domain_name: str, *, contacts: Union[DomainContacts, Contact, None] = None,
                               name_servers: Iterable[str], years: int = 1,
                               tld_attributes: Optional[Dict[str, str]] = None,
                               use_trustee_contact: bool = False) -> DomainOperationResult:
        """Register a domain with inline contact details. **Charges your balance.**

        ``contacts`` is a :class:`DomainContacts`, or one :class:`Contact` for
        all four roles. See :meth:`register`.
        """
        return self._operation(DomainRegisterWithContactsRequest(
            domain_name, contacts, list(non_blank(name_servers)), years, tld_attributes, use_trustee_contact))

    def renew(self, domain_name: str, years: int) -> DomainOperationResult:
        """Add years (1 to 10) to a domain. **Charges your balance.**

        Use :meth:`renew_check` first to see whether it is renewable and at what price.
        """
        return self._operation(DomainRenewRequest(domain_name, years))

    def renew_check(self, domain_name: str, years: int = 0) -> RenewCheck:
        """Whether a domain can be renewed for ``years`` (0 lets the API choose), and the premium price."""
        return self._send(DomainRenewCheckRequest(domain_name, years))

    def restore(self, domain_name: str) -> None:
        """Bring back a deleted domain during the redemption period. **Charges your balance.**"""
        self._send(DomainRestoreRequest(domain_name))

    # -- transfers ------------------------------------------------------------------

    def transfer(self, domain_name: str, auth_code: str = "", *, years: int = 0) -> DomainOperationResult:
        """Start an incoming transfer. **Charges your balance.**

        Check it first with :meth:`transfer_check`; follow it with :meth:`transfer_status`.
        """
        return self._operation(DomainTransferRequest(domain_name, auth_code, years))

    def transfer_check(self, domain_name: str, auth_code: str) -> TransferCheck:
        """Whether a domain can be transferred in with ``auth_code``: lock state, auth code
        validity, registry statuses and premium price."""
        return self._send(DomainTransferCheckRequest(domain_name, auth_code))

    def transfer_status(self, domain_name: str) -> TransferStatus:
        """The state of a pending incoming transfer."""
        return self._send(DomainTransferStatusRequest(domain_name))

    # -- settings -----------------------------------------------------------------------

    def lock(self, domain_name: str) -> None:
        """Turn the transfer lock on."""
        self._send(DomainLockRequest(domain_name))

    def unlock(self, domain_name: str) -> None:
        """Turn the transfer lock off, which a transfer to another registrar needs."""
        self._send(DomainUnlockRequest(domain_name))

    def set_privacy(self, domain_name: str, enabled: bool) -> None:
        """Turn WHOIS privacy protection on or off.

        TLDs without privacy answer with ``ErrorCode.PRIVACY_NOT_SUPPORTED``.
        """
        self._send(DomainPrivacyRequest(domain_name, enabled))

    def update_auth_code(self, domain_name: str) -> str:
        """Ask the registry for a new transfer auth code and return it.

        To read the current code, use ``info(...).auth_code``.
        """
        res = self._send(DomainUpdateAuthCodeRequest(domain_name))
        return res.auth_code if res is not None else ""

    def set_name_servers(self, domain_name: str, name_servers: Iterable[str], *,
                         dnssec_mode: Union[DNSSECMode, int, str] = DNSSECMode.BLOCK) -> None:
        """Replace the nameservers of a domain::

            client.domains.set_name_servers("example.com", ["ns1.example.net", "ns2.example.net"])

        ``dnssec_mode`` matters only for a DNSSEC-signed domain.
        """
        self._send(DomainNameServersSetRequest(domain_name, as_list(name_servers), dnssec_mode))

    def add_host(self, domain_name: str, host_name: str, ip_addresses: Union[str, Iterable[str]]) -> None:
        """Create a child nameserver such as ns1.example.com with one or more IPv4/IPv6 addresses."""
        self._send(DomainHostAddRequest(domain_name, host_name, as_list(ip_addresses)))

    def update_host(self, domain_name: str, host_name: str, ip_addresses: Union[str, Iterable[str]], *,
                    new_host_name: str = "") -> None:
        """Replace a child nameserver's addresses, and rename it with ``new_host_name``."""
        self._send(DomainHostUpdateRequest(domain_name, host_name, as_list(ip_addresses), new_host_name))

    def delete_host(self, domain_name: str, host_name: str) -> None:
        """Delete a child nameserver."""
        self._send(DomainHostDeleteRequest(domain_name, host_name))

    # -- contacts -------------------------------------------------------------------------

    def update_contacts(self, domain_name: str, contacts: DomainContacts) -> None:
        """Replace contacts of a domain with inline details; roles left ``None`` stay as they are::

            client.domains.update_contacts("example.com", DomainContacts(billing=billing))
        """
        self._send(DomainContactsUpdateRequest(domain_name, contacts))

    def set_contact_handles(self, domain_name: str, handles: Union[ContactHandles, str]) -> None:
        """Point contact roles of a domain at existing handles; roles left empty stay as they are::

            client.domains.set_contact_handles("example.com", ContactHandles(admin="DNA-2", tech="DNA-2"))
        """
        self._send(DomainContactsSetHandlesRequest(domain_name, handles))

    # -- documents ------------------------------------------------------------------------

    def documents(self, domain_name: str, *, types: Optional[Iterable[Any]] = None, skip: int = 0,
                  limit: int = 0, sort: str = "") -> Page[Document]:
        """One page of a domain's registry documents."""
        return self._send(DomainDocumentsListRequest(domain_name, as_list(types) or None, skip, limit, sort))

    def upload_documents(self, domain_name: str,
                         documents: Union[DocumentUpload, Iterable[DocumentUpload]]) -> DocumentUploadResult:
        """Upload registry documents for a domain::

            doc = DocumentUpload.from_file(DocumentType.IDENTITY_CARD, "id.pdf")
            client.domains.upload_documents("example.com.tr", doc)
        """
        return self._send(DomainDocumentsUploadRequest(domain_name, as_list(documents)))

    # -- forwarding -------------------------------------------------------------------------

    def forwarding(self, domain_name: str) -> Optional[Forwarding]:
        """The URL forwarding of a domain, or ``None`` when it has none."""
        try:
            f = self._send(DomainForwardGetRequest(domain_name))
        except APIError as err:
            if err.code == ErrorCode.FORWARDING_NOT_FOUND:
                return None
            raise
        if f is None or not f.url.strip():
            return None
        return f

    def set_forwarding(self, domain_name: str, url: str,
                       forward_type: Union[ForwardType, str] = ForwardType.STANDARD) -> None:
        """Forward a domain to ``url`` with a redirect (``STANDARD``) or a frame (``FRAME``)."""
        self._send(DomainForwardSetRequest(domain_name, url, forward_type))

    def delete_forwarding(self, domain_name: str) -> None:
        """Remove the URL forwarding of a domain. Also succeeds when it had none."""
        try:
            self._send(DomainForwardDeleteRequest(domain_name))
        except APIError as err:
            if err.code != ErrorCode.FORWARDING_NOT_FOUND:
                raise

    # -- helpers ----------------------------------------------------------------------------

    def _operation(self, req: BaseRequest) -> DomainOperationResult:
        resp = self._exchange(req)
        res: DomainOperationResult = resp.value
        if res is None or not res.success:
            raise self._failed(req, resp, "", res.message if res is not None else "")
        return res
