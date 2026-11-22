"""Named values for the numbers and strings the API uses.

Integer enums (:class:`DomainStatus`, :class:`OrderType`, ...) are
:class:`enum.IntEnum` subclasses: they compare equal to the API's numbers and
print as the API's names::

    >>> DomainStatus.PENDING_DELETE == 7
    True
    >>> str(DomainStatus.PENDING_DELETE)
    'PendingDelete'
    >>> DomainStatus.parse("pendingdelete")
    <DomainStatus.PENDING_DELETE: 7>

``parse`` accepts the API name or the member name in any case, or the number,
and raises :class:`ValueError` listing the allowed values. When decoding a
response, values this package does not know yet do not fail: they become a
member whose ``is_known`` is ``False``.

String enums (:class:`ContactType`, :class:`RecordType`, ...) are ``str``
subclasses whose value is exactly what the API expects.
"""

from __future__ import annotations

import enum
from typing import Any, Optional, Type, TypeVar

E = TypeVar("E", bound="ApiIntEnum")
S = TypeVar("S", bound="ApiStrEnum")

__all__ = [
    "AccountCurrency",
    "ApiIntEnum",
    "ApiStrEnum",
    "AuthenticationType",
    "ChargeType",
    "ContactType",
    "DNSSECAlgorithm",
    "DNSSECMode",
    "DNSSECOperationType",
    "DNSSECStatus",
    "DSDigestType",
    "DSRecordStatus",
    "DocumentOperationType",
    "DocumentStatus",
    "DocumentType",
    "DomainStatus",
    "ForwardType",
    "IPVersion",
    "OrderProductStatus",
    "OrderStatus",
    "OrderType",
    "ProductType",
    "RecordType",
    "ResellerStatus",
    "TransactionStatus",
    "TransactionType",
    "WebServerType",
]


def _norm(text: str) -> str:
    return text.strip().replace("_", "").replace("-", "").replace(" ", "").lower()


class ApiIntEnum(enum.IntEnum):
    """Base of the integer enums: members are ``NAME = number, "ApiName"``."""

    label: str

    def __new__(cls, value: int, label: str = ""):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj

    def __str__(self) -> str:
        return self.label

    def __format__(self, spec: str) -> str:
        return format(self.label, spec)

    @property
    def is_known(self) -> bool:
        """``False`` for a value the API sent that this package has no name for."""
        return self._name_ in type(self).__members__

    @classmethod
    def _unknown(cls, value: int, label: str = ""):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._name_ = "UNKNOWN"
        obj.label = label or "%s(%d)" % (cls.__name__, value)
        return obj

    @classmethod
    def _lookup(cls: Type[E], value: Any) -> Optional[E]:
        if isinstance(value, cls):
            return value
        if isinstance(value, bool):
            return None
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        if isinstance(value, int):
            return cls._value2member_map_.get(value)  # type: ignore[return-value]
        if isinstance(value, str):
            key = _norm(value)
            for member in cls:
                if _norm(member.label) == key or _norm(member.name) == key:
                    return member
            try:
                return cls._value2member_map_.get(int(value.strip()))  # type: ignore[return-value]
            except ValueError:
                return None
        return None

    @classmethod
    def parse(cls: Type[E], value: Any) -> E:
        """Return the member for a name ("PendingDelete", "pending_delete") or number.

        Raises :class:`ValueError` for anything else.
        """
        member = cls._lookup(value)
        if member is None:
            raise ValueError("%r is not a valid %s (allowed: %s)" % (
                value, cls.__name__, ", ".join(m.label for m in cls)))
        return member

    @classmethod
    def from_api(cls: Type[E], value: Any) -> Optional[E]:
        """Decode a value from a response: never raises; ``None`` when absent."""
        if value is None or value == "":
            return None
        member = cls._lookup(value)
        if member is not None:
            return member
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return cls._unknown(int(value))
        return cls._unknown(-1, str(value))


class ApiStrEnum(str, enum.Enum):
    """Base of the string enums: the value is exactly what the API expects."""

    def __str__(self) -> str:
        return str(self.value)

    def __format__(self, spec: str) -> str:
        return format(str(self.value), spec)

    @classmethod
    def _aliases(cls) -> dict:
        return {}

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            key = _norm(value)
            alias = cls._aliases().get(key)
            if alias is not None:
                return cls(alias)
            for member in cls:
                if _norm(member.value) == key or _norm(member.name) == key:
                    return member
        return None

    @classmethod
    def from_api(cls, value: Any) -> Any:
        """Decode a value from a response: the member, or the text as sent when unknown; ``None`` when absent."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        try:
            return cls(value)
        except ValueError:
            return str(value).strip()

    @classmethod
    def parse(cls: Type[S], value: Any) -> S:
        """Return the member for a value in any case; raises :class:`ValueError`."""
        try:
            return cls(value)
        except ValueError:
            raise ValueError("%r is not a valid %s (allowed: %s)" % (
                value, cls.__name__, ", ".join(m.value for m in cls))) from None


# ---------------------------------------------------------------------------
# Domains


class DomainStatus(ApiIntEnum):
    """The lifecycle state of a domain."""

    ACTIVE = 0, "Active"
    WAITING_FOR_REGISTRATION = 1, "WaitingForRegistration"
    #: Registry documents must be uploaded (``domains.upload_documents``).
    WAITING_FOR_DOCUMENT = 2, "WaitingForDocument"
    #: Internal transfer from another reseller.
    WAITING_FOR_INCOMING_TRANSFER = 3, "WaitingForIncomingTransfer"
    #: Moved to another registrar.
    TRANSFERRED_OUT = 4, "TransferredOut"
    #: An incoming transfer was rejected.
    TRANSFER_REJECTED = 5, "TransferRejected"
    #: In the redemption period; ``domains.restore`` may bring it back.
    PENDING_DELETE = 7, "PendingDelete"
    DELETED = 8, "Deleted"
    #: Transfer confirmation e-mail sent.
    CONFIRMATION_EMAIL_SEND = 9, "ConfirmationEmailSend"
    #: Transfer to another registrar in progress.
    WAITING_FOR_OUTGOING_TRANSFER = 11, "WaitingForOutgoingTransfer"
    #: Suspended, e.g. the registrant e-mail was not verified within 15 days.
    PENDING_HOLD = 12, "PendingHold"
    MODIFICATION_PENDING = 15, "ModificationPending"
    #: Subject to a legal process.
    IN_CASE = 18, "InCase"
    PENDING_RESTORE = 19, "PendingRestore"


class ContactType(ApiStrEnum):
    """A contact role. A registration needs all four."""

    REGISTRANT = "Registrant"
    ADMIN = "Admin"
    TECH = "Tech"
    BILLING = "Billing"

    @classmethod
    def _aliases(cls) -> dict:
        return {"owner": "Registrant", "administrative": "Admin", "technical": "Tech"}


class ForwardType(ApiStrEnum):
    """A URL forwarding mode."""

    #: HTTP 301 redirect (the default).
    STANDARD = "Standard"
    #: Shows the target in a frame (masked URL).
    FRAME = "Frame"


class DNSSECMode(ApiIntEnum):
    """What to do with DNSSEC when the nameservers of a signed domain change."""

    #: Reject the change while DS records exist (the default).
    BLOCK = 0, "Block"
    #: Keep the DS records: you confirm the new DNS provider serves a matching DNSKEY.
    KEEP = 1, "KeepDnssec"
    #: Remove all DS records first, then change the nameservers.
    DISABLE = 2, "DisableDnssec"


class IPVersion(ApiStrEnum):
    """The IP version of a child nameserver address."""

    V4 = "v4"
    #: Rejected when the TLD has no IPv6 glue.
    V6 = "v6"


# ---------------------------------------------------------------------------
# Documents


class DocumentType(ApiIntEnum):
    """The kind of a registry document (mostly for .tr domains)."""

    IDENTITY_CARD = 1, "IdentityCard"
    PASSPORT = 2, "Passport"
    TAX_CERTIFICATE = 3, "TaxCertificate"
    ACTIVITY_CERTIFICATE = 4, "ActivityCertificate"
    SIGNATURE_CIRCULAR = 5, "SignatureCircular"
    AUTHORIZATION_LETTER = 6, "AuthorizationLetter"
    PETITION = 7, "Petition"
    TRADE_REGISTRY_GAZETTE = 8, "TradeRegistryGazette"
    TRADEMARK_CERTIFICATE = 9, "TrademarkCertificate"
    #: .edu.tr
    EDUCATION_CERTIFICATE = 10, "EducationCertificate"
    #: .org.tr
    ORGANIZATION_STATUTE = 11, "OrganizationStatute"
    #: .gov.tr, .bank, .mil.tr
    GOVERNMENT_APPROVAL = 12, "GovernmentApproval"
    DOMAIN_OWNERSHIP_PROOF = 13, "DomainOwnershipProof"
    POWER_OF_ATTORNEY = 14, "PowerOfAttorney"
    #: .av.tr
    BAR_ASSOCIATION_CERTIFICATE = 15, "BarAssociationCertificate"
    #: .dr.tr
    MEDICAL_DIPLOMA_OR_LICENSE = 16, "MedicalDiplomaOrLicense"
    #: .bel.tr
    MUNICIPAL_OFFICIAL_LETTER = 17, "MunicipalOfficialLetter"
    #: .k12.tr, .edu.tr
    EDUCATION_INSTITUTION_LICENSE = 18, "EducationInstitutionLicense"
    CHAMBER_OF_COMMERCE_CERTIFICATE = 19, "ChamberOfCommerceCertificate"
    TRADEMARK_TRANSFER_AGREEMENT = 20, "TrademarkTransferAgreement"
    #: .kep.tr
    KEP_AUTHORIZATION = 21, "KepAuthorization"
    OTHER = 99, "Other"


class DocumentStatus(ApiIntEnum):
    """The review state of a registry document."""

    #: Expected, not uploaded.
    WAITING = 1, "Waiting"
    #: Uploaded, not reviewed yet.
    PENDING = 2, "Pending"
    APPROVED = 3, "Approved"
    REJECTED = 4, "Rejected"
    EXPIRED = 5, "Expired"
    #: Application or owner change cancelled.
    CANCELLED = 6, "Cancelled"


class DocumentOperationType(ApiIntEnum):
    """The operation a document was requested for."""

    #: New registration.
    CREATE = 1, "Create"
    #: Trade / registrant change.
    OWNER_CHANGE = 2, "OwnerChange"
    DELETE = 3, "Delete"


# ---------------------------------------------------------------------------
# DNS and DNSSEC


class RecordType(ApiStrEnum):
    """A DNS record type, with the exact case the zone API expects.

    Requests accept any case (``"txt"`` is sent as ``TXT``, ``"dnskey"`` as ``DNSKey``).
    """

    A = "A"
    AAAA = "AAAA"
    #: A CNAME-like record allowed at the apex.
    ALIAS = "ALIAS"
    NS = "NS"
    #: Needs a name: not allowed at the apex.
    CNAME = "CNAME"
    #: Content is "PRIORITY HOST", e.g. "10 mail.example.com".
    MX = "MX"
    SOA = "SOA"
    #: The API adds the surrounding quotes.
    TXT = "TXT"
    PTR = "PTR"
    SRV = "SRV"
    DNSKEY = "DNSKey"
    DS = "DS"
    NSEC = "NSEC"
    NSEC3 = "NSEC3"
    NSEC3PARAM = "NSEC3Param"
    RRSIG = "RRSIG"
    AFSDB = "AFSDB"
    ATMA = "ATMA"
    #: Content has exactly 3 parts: 0 issue "letsencrypt.org".
    CAA = "CAA"
    CERT = "CERT"
    DHCID = "DHCID"
    DNAME = "DName"
    HINFO = "HInfo"
    ISDN = "ISDN"
    LOC = "LOC"
    MB = "MB"
    MG = "MG"
    MINFO = "MInfo"
    MR = "MR"
    NAPTR = "NAPTR"
    NSAP = "NSAP"
    RP = "RP"
    RT = "RT"
    TLSA = "TLSA"
    X25 = "X25"


class DNSSECStatus(ApiIntEnum):
    """The DNSSEC state of a domain."""

    #: No DS record at the registry.
    UNSIGNED = 0, "Unsigned"
    #: DS add sent, awaiting confirmation.
    PENDING_ENABLE = 1, "PendingEnable"
    #: At least one active DS record.
    SIGNED = 2, "Signed"
    #: DS removal sent, awaiting confirmation.
    PENDING_DISABLE = 3, "PendingDisable"
    #: The last DNSSEC operation failed.
    ERROR = 4, "Error"


class DNSSECOperationType(ApiIntEnum):
    """The kind of a DNSSEC operation."""

    ADD = 0, "Add"
    REMOVE = 1, "Remove"
    REMOVE_ALL = 2, "RemoveAll"
    SYNC = 3, "Sync"


class DSRecordStatus(ApiIntEnum):
    """The state of a DS record. Several can be active during a key rollover."""

    PENDING = 0, "Pending"
    ACTIVE = 1, "Active"
    REMOVING = 2, "Removing"
    REMOVED = 3, "Removed"
    FAILED = 4, "Failed"


class DNSSECAlgorithm(ApiIntEnum):
    """An IANA DNSSEC algorithm number."""

    RSAMD5 = 1, "RsaMd5"
    DSA = 3, "Dsa"
    RSASHA1 = 5, "RsaSha1"
    DSA_NSEC3_SHA1 = 6, "DsaNsec3Sha1"
    RSASHA1_NSEC3_SHA1 = 7, "RsaSha1Nsec3Sha1"
    RSASHA256 = 8, "RsaSha256"
    RSASHA512 = 10, "RsaSha512"
    ECC_GOST = 12, "EccGost"
    ECDSAP256SHA256 = 13, "EcdsaP256Sha256"
    ECDSAP384SHA384 = 14, "EcdsaP384Sha384"
    ED25519 = 15, "Ed25519"
    ED448 = 16, "Ed448"


class DSDigestType(ApiIntEnum):
    """An IANA DS digest type."""

    SHA1 = 1, "Sha1"
    SHA256 = 2, "Sha256"
    GOST = 3, "Gost"
    SHA384 = 4, "Sha384"


# ---------------------------------------------------------------------------
# SSL


class AuthenticationType(ApiStrEnum):
    """The domain control validation method of a certificate."""

    #: Approval e-mail to the approver address.
    EMAIL = "Email"
    #: DNS CNAME record.
    CNAME = "Cname"
    #: HTTP file on the site.
    HTTP = "Http"
    #: File-based validation.
    FILE = "File"


class WebServerType(ApiStrEnum):
    """The web server software a certificate is issued for."""

    APACHE = "Apache"
    IIS = "IIS"
    AOL = "AOL"
    C2NET = "C2Net"


# ---------------------------------------------------------------------------
# Account, orders and products


class AccountCurrency(ApiIntEnum):
    """The currency a reseller account is kept in."""

    TRY = 1, "TRY"
    USD = 2, "USD"
    EURO = 3, "EURO"


class ResellerStatus(ApiIntEnum):
    """The state of a reseller account."""

    ACTIVE = 0, "Active"
    #: The account still has to be verified (e-mail, SMS, ...).
    WAITING_FOR_APPROVAL = 1, "WaitingForApproval"
    #: Access to the account is blocked.
    SUSPEND = 2, "Suspend"
    #: A new reseller that has not completed the sign-up wizard yet.
    WAITING_FOR_COMPLETION_WIZARD = 3, "WaitingForCompletionWizard"


class TransactionType(ApiIntEnum):
    """The kind of a balance transaction."""

    REGISTER = 1, "Register"
    RENEW = 2, "Renew"
    TRANSFER = 3, "Transfer"
    RESTORE = 4, "Restore"
    DEPOSIT = 5, "Deposit"
    BACKORDER = 6, "Backorder"
    REFUND = 7, "Refund"
    DEDUCTION = 8, "Deduction"
    PRE_REGISTER = 9, "PreRegister"
    SHOPPING = 10, "Shopping"
    RESELLER_PAYMENT = 11, "ResellerPayment"
    INTERNAL_TRANSFER = 12, "InternalTransfer"


class TransactionStatus(ApiIntEnum):
    """The outcome of a balance transaction."""

    FAILED = 0, "Failed"
    SUCCESS = 1, "Success"
    CANCELED = 2, "Canceled"
    PROCESSING = 3, "Processing"
    REFUNDED = 4, "Refunded"


class ChargeType(ApiIntEnum):
    """The direction of a balance transaction."""

    #: Credit.
    ADD = 0, "Add"
    #: Debit.
    SUBTRACT = 1, "Subtract"


class ProductType(ApiIntEnum):
    """The kind of a product."""

    DOMAIN = 1, "Domain"
    SSL = 2, "SSL"
    DEPOSIT = 3, "Deposit"
    DOMAIN_TRUSTEE = 4, "DomainTrustee"
    HOSTING = 5, "Hosting"
    OWNER_CHANGE = 6, "OwnerChange"


class OrderType(ApiIntEnum):
    """The kind of an order."""

    REGISTER = 1, "Register"
    RENEW = 2, "Renew"
    TRANSFER = 3, "Transfer"
    RESTORE = 4, "Restore"
    SUBRESELLER_TRANSFER = 5, "SubresellerTransfer"
    BACKORDER = 6, "Backorder"
    INTERNAL_TRANSFER = 7, "InternalTransfer"
    CHARGE = 8, "Charge"
    TRUSTEE = 9, "Trustee"
    LEASING = 10, "Leasing"
    CREATE = 11, "Create"
    OWNER_CHANGE = 12, "OwnerChange"


class OrderStatus(ApiIntEnum):
    """The state of an order."""

    ACTIVE = 1, "Active"
    PENDING = 2, "Pending"
    CANCELED = 3, "Canceled"
    IN_PROGRESS = 4, "InProgress"


class OrderProductStatus(ApiIntEnum):
    """The state of an order line."""

    ORDERED = 1, "Ordered"
    CANCELED = 2, "Canceled"
    IN_PROGRESS = 3, "InProgress"
