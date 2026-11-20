"""Contacts and reusable contact handles. CLI: ``dna contact ...``

Create a contact once with ``client.contacts.create(...)``, then register
domains with its handle. :class:`Contact` is also what a domain's contacts
look like in ``client.domains.info(...)``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from ._service import Service
from .enums import ContactType
from .errors import APIError, ErrorCode
from .model import Model, boolean, enum_value, integer, model, model_list, optional_boolean, text, timestamp
from .request import BaseRequest, Safety, Validator

__all__ = [
    "Contact",
    "ContactCreateRequest",
    "ContactCreateResult",
    "ContactDetails",
    "ContactGetRequest",
    "ContactHandles",
    "ContactResendVerificationRequest",
    "ContactService",
    "ContactUpdateRequest",
    "ContactUpdateResult",
    "ContactUpdateStats",
    "ContactVerification",
    "ContactVerificationRequest",
    "AffectedDomain",
    "DomainContacts",
]

_NON_DIGITS = re.compile(r"\D")


def digits(value: Optional[str]) -> str:
    """Keep only the digits: ``"+90 (555) 123-45-67"`` becomes ``"905551234567"``."""
    return _NON_DIGITS.sub("", value or "")


# ---------------------------------------------------------------------------
# Models


@dataclass
class Contact(Model):
    """A person or organisation in a contact role.

    Requests tidy a contact before sending it: every field is trimmed, the
    country is upper-cased and the phone and fax fields keep only their
    digits (``"+90 (555) 123-45-67"`` works).
    """

    first_name: str = text("firstName")
    last_name: str = text("lastName")
    #: Optional.
    company_name: str = text("companyName")
    email: str = text("eMail")
    address: str = text("address")
    city: str = text("city")
    #: Required; repeat the city when there is none.
    state: str = text("state")
    postal_code: str = text("postalCode")
    #: The ISO 3166-1 alpha-2 code, e.g. ``"TR"`` (``"GB"``, not ``"UK"``).
    country: str = text("country")
    #: The calling code without "+", e.g. ``"90"``.
    phone_country_code: str = text("phoneCountryCode")
    #: The number without the calling code, e.g. ``"5551234567"``.
    phone: str = text("phone")
    fax_country_code: str = text("faxCountryCode")
    fax: str = text("fax")
    #: Publish the contact in WHOIS. Leave it ``None`` to keep the registry default (recommended).
    disclose_flag: Optional[bool] = optional_boolean("discloseFlag")
    #: The role. The API sets it on the contacts of a domain; requests that need it set it themselves.
    type: Optional[ContactType] = enum_value("contactType", ContactType)
    #: The contact's handle, e.g. ``"DNA-12345"``. Set by the API.
    handle: str = text("handle")

    def normalized(self) -> "Contact":
        """A tidied copy, as sent to the API."""
        t = _strip
        return replace(
            self,
            first_name=t(self.first_name), last_name=t(self.last_name), company_name=t(self.company_name),
            email=t(self.email), address=t(self.address), city=t(self.city), state=t(self.state),
            postal_code=t(self.postal_code), country=t(self.country).upper(),
            phone_country_code=digits(self.phone_country_code), phone=digits(self.phone),
            fax_country_code=digits(self.fax_country_code), fax=digits(self.fax), handle=t(self.handle),
        )

    def validate(self, v: Validator, prefix: str = "") -> None:
        """Record the fields the API requires, with ``prefix`` in front of each field name."""
        c = self.normalized()
        f = lambda name: prefix + name  # noqa: E731
        v.required(f("first_name"), c.first_name)
        v.required(f("last_name"), c.last_name)
        v.required(f("email"), c.email)
        v.check(not c.email or "@" in c.email, f("email"), "is not an e-mail address")
        v.required(f("address"), c.address)
        v.required(f("city"), c.city)
        v.required(f("state"), c.state)
        v.required(f("postal_code"), c.postal_code)
        v.required(f("country"), c.country)
        v.check(not c.country or len(c.country) == 2, f("country"), "must be a 2-letter ISO code such as TR or US")
        v.required(f("phone_country_code"), c.phone_country_code)
        v.check(len(c.phone_country_code) <= 3, f("phone_country_code"), "must be at most 3 digits, e.g. 90")
        v.required(f("phone"), c.phone)
        v.check(len(c.phone) <= 16, f("phone"), "must be at most 16 digits")
        v.max_length(f("first_name"), c.first_name, 80)
        v.max_length(f("last_name"), c.last_name, 80)
        v.max_length(f("company_name"), c.company_name, 256)
        v.max_length(f("address"), c.address, 256)
        v.max_length(f("city"), c.city, 80)
        v.max_length(f("state"), c.state, 80)
        v.max_length(f("postal_code"), c.postal_code, 15)

    def to_api(self, role: Optional[ContactType] = None) -> Dict[str, Any]:
        """The JSON object the API expects (``ContactInformationDto``, plus the role when given)."""
        c = self.normalized()
        out: Dict[str, Any] = {
            "firstName": c.first_name,
            "lastName": c.last_name,
            "eMail": c.email,
            "address": c.address,
            "city": c.city,
            "state": c.state,
            "postalCode": c.postal_code,
            "country": c.country,
            "phoneCountryCode": c.phone_country_code,
            "phone": c.phone,
        }
        if c.company_name:
            out["companyName"] = c.company_name
        if c.fax_country_code:
            out["faxCountryCode"] = c.fax_country_code
        if c.fax:
            out["fax"] = c.fax
        if c.disclose_flag is not None:
            out["discloseFlag"] = bool(c.disclose_flag)
        if role is not None:
            out["contactType"] = ContactType.parse(role).value
        return out


def _strip(value: Optional[str]) -> str:
    return (value or "").strip()


ROLES: Tuple[ContactType, ...] = (ContactType.REGISTRANT, ContactType.ADMIN, ContactType.TECH, ContactType.BILLING)


@dataclass
class ContactHandles:
    """The contact handle of each role. Roles left empty are not sent."""

    registrant: str = ""
    admin: str = ""
    tech: str = ""
    billing: str = ""

    @classmethod
    def same(cls, handle: str) -> "ContactHandles":
        """One handle for all four roles."""
        return cls(handle, handle, handle, handle)

    @classmethod
    def coerce(cls, value: Union["ContactHandles", str, None]) -> "ContactHandles":
        """A handle string means the same handle for all four roles."""
        if value is None:
            return cls()
        if isinstance(value, str):
            return cls.same(value)
        return value

    def items(self) -> List[Tuple[ContactType, str]]:
        """The roles that are set, as ``(role, handle)``, in the order Registrant, Admin, Tech, Billing."""
        pairs = zip(ROLES, (self.registrant, self.admin, self.tech, self.billing))
        return [(role, h.strip()) for role, h in pairs if h and h.strip()]

    def to_api(self) -> List[Dict[str, str]]:
        return [{"contactType": role.value, "handle": h} for role, h in self.items()]

    def validate(self, v: Validator, field_name: str, require_all: bool) -> None:
        n = len(self.items())
        if require_all and n < 4:
            v.add(field_name, "needs a handle for every role (registrant, admin, tech, billing); "
                              "ContactHandles.same() sets all four")
        elif n == 0:
            v.add(field_name, "needs at least one handle")


@dataclass
class DomainContacts:
    """The contact of each role. Roles left ``None`` are not sent."""

    registrant: Optional[Contact] = None
    admin: Optional[Contact] = None
    tech: Optional[Contact] = None
    billing: Optional[Contact] = None

    @classmethod
    def same(cls, contact: Contact) -> "DomainContacts":
        """One contact for all four roles."""
        return cls(contact, contact, contact, contact)

    @classmethod
    def coerce(cls, value: Union["DomainContacts", Contact, None]) -> "DomainContacts":
        """A single :class:`Contact` means the same contact for all four roles."""
        if value is None:
            return cls()
        if isinstance(value, Contact):
            return cls.same(value)
        return value

    def items(self) -> Iterator[Tuple[ContactType, Optional[Contact]]]:
        return iter(zip(ROLES, (self.registrant, self.admin, self.tech, self.billing)))

    def to_api(self) -> List[Dict[str, Any]]:
        """The contacts that are set, each with its role."""
        return [c.to_api(role) for role, c in self.items() if c is not None]

    def validate(self, v: Validator, field_name: str, require_all: bool) -> None:
        for role, c in self.items():
            name = role.value.lower()
            if c is not None:
                c.validate(v, "%s.%s." % (field_name, name))
            elif require_all:
                v.add("%s.%s" % (field_name, name), "is required (DomainContacts.same() sets all four roles)")
        if not require_all and not self.to_api():
            v.add(field_name, "needs at least one contact")


@dataclass
class ContactVerification(Model):
    """The e-mail or phone verification state of a contact.

    A domain stays usable after registration, but when the registrant e-mail
    is not verified within 15 days the domain is put on hold.
    """

    owner_name: str = text("ownerName")
    #: The e-mail address or phone number.
    field_value: str = text("fieldValue")
    field_type: str = text("fieldType")
    operation_status: str = text("operationStatus")
    verified: bool = boolean("isUserVerified")
    verified_at: Optional[datetime] = timestamp("userVerificationDate")
    created_at: Optional[datetime] = timestamp("createdDate")
    token_expires_at: Optional[datetime] = timestamp("tokenExpireDate")
    resent_at: Optional[datetime] = timestamp("resendDate")
    resend_retry_count: int = integer("resendRetryCount")
    last_attempt_at: Optional[datetime] = timestamp("lastAttemptDate")
    attempt_number: int = integer("attemptNumber")


@dataclass
class ContactDetails(Model):
    """A contact handle with its verification state."""

    contact: Contact = model("contact", Contact)
    verifications: List[ContactVerification] = model_list("verificationObjects", ContactVerification)


@dataclass
class ContactCreateResult(Model):
    """The API's answer to :class:`ContactCreateRequest`."""

    handle: str = text("handle")
    message: str = text("operationMessage")
    success: bool = boolean("isSuccess")


@dataclass
class ContactUpdateStats(Model):
    """How many domains a contact update touched, and with what result."""

    total_domain_count: int = integer("totalDomainCount")
    success_count: int = integer("successCount")
    pending_document_count: int = integer("pendingDocumentCount")
    failed_count: int = integer("failedCount")
    split_count: int = integer("splitCount")


@dataclass
class AffectedDomain(Model):
    """A domain touched by a contact update."""

    domain_name: str = text("domainName")
    status: str = text("status")
    #: Some registries cannot share a handle and get a new one: store it when it is set.
    new_handle: str = text("newHandle")
    reason: str = text("reason")
    message: str = text("message")


@dataclass
class ContactUpdateResult(Model):
    """The API's answer to :class:`ContactUpdateRequest`: the contact and every domain using it."""

    handle: str = text("handle")
    success: bool = boolean("contactUpdateSuccess")
    stats: ContactUpdateStats = model("stats", ContactUpdateStats)
    affected_domains: List[AffectedDomain] = model_list("affectedDomains", AffectedDomain)


@dataclass
class _VerificationList(Model):
    results: List[ContactVerification] = model_list("results", ContactVerification)


# ---------------------------------------------------------------------------
# Requests


@dataclass
class ContactGetRequest(BaseRequest):
    """Read a contact handle. CLI: ``dna contact get``"""

    method = "GET"
    path = "/api/v1/contacts/{handle}"
    safety = Safety.READ
    response = ContactDetails

    handle: str = ""

    def validate(self, v: Validator) -> None:
        v.required("handle", self.handle)


@dataclass
class ContactCreateRequest(BaseRequest):
    """Create a contact handle. CLI: ``dna contact create``"""

    method = "POST"
    path = "/api/v1/contacts"
    safety = Safety.WRITE
    response = ContactCreateResult

    contact: Contact = field(default_factory=Contact)

    def body(self) -> Dict[str, Any]:
        return {"contact": self.contact.to_api()}

    def validate(self, v: Validator) -> None:
        self.contact.validate(v, "contact.")


@dataclass
class ContactUpdateRequest(BaseRequest):
    """Replace a contact handle's details, and those of every domain using it.

    CLI: ``dna contact update``
    """

    method = "PUT"
    path = "/api/v1/contacts/{handle}"
    safety = Safety.WRITE
    response = ContactUpdateResult

    handle: str = ""
    #: The complete new contact: the update is a full replacement, not a patch.
    contact: Contact = field(default_factory=Contact)

    def body(self) -> Dict[str, Any]:
        return {"contact": self.contact.to_api()}

    def validate(self, v: Validator) -> None:
        v.required("handle", self.handle)
        self.contact.validate(v, "contact.")


@dataclass
class ContactVerificationRequest(BaseRequest):
    """Read the verification state of a contact. CLI: ``dna contact verification``"""

    method = "GET"
    path = "/api/v1/contacts/verification/check"
    safety = Safety.READ
    response = _VerificationList

    handle: str = ""

    def query(self):
        return [("HandleCode", self.handle.strip())]

    def validate(self, v: Validator) -> None:
        v.required("handle", self.handle)


@dataclass
class ContactResendVerificationRequest(BaseRequest):
    """Send the verification notice again. CLI: ``dna contact resend-verification``"""

    method = "POST"
    path = "/api/v1/contacts/verification/request"
    safety = Safety.WRITE

    handle: str = ""

    def body(self) -> Dict[str, Any]:
        return {"handleCode": self.handle.strip()}

    def validate(self, v: Validator) -> None:
        v.required("handle", self.handle)


# ---------------------------------------------------------------------------
# Service


class ContactService(Service):
    """Reusable contact handles. CLI: ``dna contact``"""

    __slots__ = ()

    def get(self, handle: str) -> ContactDetails:
        """A contact handle and its verification state."""
        return self._send(ContactGetRequest(handle))

    def create(self, contact: Contact) -> str:
        """Create a contact and return its handle, which ``domains.register`` accepts."""
        req = ContactCreateRequest(contact)
        resp = self._exchange(req)
        res: ContactCreateResult = resp.value
        if res is None or not res.success or not res.handle:
            raise self._failed(req, resp, "", res.message if res else "")
        return res.handle

    def update(self, handle: str, contact: Contact) -> ContactUpdateResult:
        """Replace the details of a contact handle.

        Every domain using the handle is updated too; the result reports each of them.
        """
        req = ContactUpdateRequest(handle, contact)
        resp = self._exchange(req)
        res: ContactUpdateResult = resp.value
        if res is None or not res.success:
            raise self._failed(req, resp, "", "the contact could not be updated")
        return res

    def verification(self, handle: str) -> List[ContactVerification]:
        """The e-mail and phone verification state of a contact."""
        res = self._send(ContactVerificationRequest(handle))
        return res.results if res is not None else []

    def resend_verification(self, handle: str) -> None:
        """Send the verification notice of a contact again.

        Also succeeds when there is nothing to verify (already verified, or nothing pending).
        """
        try:
            self._send(ContactResendVerificationRequest(handle))
        except APIError as err:
            if err.code not in (ErrorCode.VERIFICATION_ALREADY_DONE, ErrorCode.VERIFICATION_NOT_PENDING):
                raise
