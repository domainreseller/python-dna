"""SSL certificates. CLI: ``dna ssl ...``

The flow: find a package with ``client.products.ssls()``, :meth:`~SSLService.generate_csr`
(or bring your own), :meth:`~SSLService.initialize` (charges the balance),
:meth:`~SSLService.configure` within 15 days, then poll :meth:`~SSLService.status`
until the certificate is issued and download it with :meth:`~SSLService.content`.

A domain can have several certificates, so an existing certificate is
addressed by its **certificate id** (a GUID), never by its domain name:
:meth:`~SSLService.initialize` and :meth:`~SSLService.renew` return it as
``result.certificate_id`` (store it), and :meth:`~SSLService.list` finds it
again by domain name.

To renew, call :meth:`~SSLService.renew` (charges the balance) and then
:meth:`~SSLService.configure` with the id it returns. Calling
:meth:`~SSLService.initialize` again is not a renewal: it buys an unrelated
certificate at the purchase price.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Dict, Iterable, Iterator, List, Optional, Union

from ._service import Service
from .contacts import digits
from .enums import AuthenticationType, WebServerType
from .model import Model, Page, boolean, model, model_list, page_of, paginate, text, texts, timestamp
from .request import BaseRequest, Body, Query, Safety, Validator, as_list, non_blank, strip, validate_paging

__all__ = [
    "CSR",
    "CSRInfo",
    "Certificate",
    "CertificateConfiguration",
    "CertificateContent",
    "CertificateIssue",
    "CertificateListItem",
    "CertificateStatus",
    "CertificateSubscription",
    "SSLApproversRequest",
    "SSLCheckCSRRequest",
    "SSLConfigureRequest",
    "SSLContact",
    "SSLContentRequest",
    "SSLGenerateCSRRequest",
    "SSLGetRequest",
    "SSLInitializeRequest",
    "SSLListRequest",
    "SSLOperationResult",
    "SSLReissueRequest",
    "SSLRenewRequest",
    "SSLRevokeRequest",
    "SSLService",
    "SSLStatusRequest",
]


# ---------------------------------------------------------------------------
# Models


@dataclass
class SSLContact(Model):
    """The contact of a certificate order."""

    first_name: str = text("firstName")
    last_name: str = text("lastName")
    company_name: str = text("companyName")
    email: str = text("eMail")
    address: str = text("address")
    city: str = text("city")
    postal_code: str = text("postalCode")
    #: The 2-letter ISO code.
    country: str = text("country")
    phone_country_code: str = text("phoneCountryCode")
    phone: str = text("phone")
    #: Optional.
    title: str = text("title")
    #: Optional.
    state: str = text("state")
    fax_country_code: str = text("faxCountryCode")
    fax: str = text("fax")
    #: The contact's role, set by the API.
    type: str = text("type")

    def normalized(self) -> "SSLContact":
        t = strip
        return replace(
            self, title=t(self.title), first_name=t(self.first_name), last_name=t(self.last_name),
            company_name=t(self.company_name), email=t(self.email), address=t(self.address), city=t(self.city),
            state=t(self.state), postal_code=t(self.postal_code), country=t(self.country).upper(),
            phone_country_code=digits(self.phone_country_code), phone=digits(self.phone),
            fax_country_code=digits(self.fax_country_code), fax=digits(self.fax), type="",
        )

    def validate(self, v: Validator, prefix: str = "contact.") -> None:
        c = self.normalized()
        for name in ("first_name", "last_name", "company_name", "email", "address", "city", "postal_code",
                     "country", "phone_country_code", "phone"):
            v.required(prefix + name, getattr(c, name))
        for name, limit in (("first_name", 70), ("last_name", 70), ("company_name", 150), ("address", 200),
                            ("city", 20), ("state", 20), ("postal_code", 10), ("phone", 15)):
            v.max_length(prefix + name, getattr(c, name), limit)

    def to_api(self) -> Dict[str, Any]:
        c = self.normalized()
        out = Body(firstName=c.first_name, lastName=c.last_name, companyName=c.company_name, eMail=c.email,
                   address=c.address, city=c.city, postalCode=c.postal_code, country=c.country,
                   phoneCountryCode=c.phone_country_code, phone=c.phone)
        return (out.set("title", c.title).set("state", c.state).set("faxCountryCode", c.fax_country_code)
                .set("fax", c.fax))


@dataclass
class CSR(Model):
    """A certificate signing request and its private key."""

    csr: str = text("csr")
    #: Needed to install the certificate. Store it safely.
    private_key: str = text("privateKey")


@dataclass
class CSRInfo(Model):
    """The decoded subject of a CSR."""

    domain_name: str = text("domainName")
    country: str = text("country")
    state: str = text("state")
    locality: str = text("locality")
    organization: str = text("organization")
    organization_unit: str = text("organizationUnit")
    alternative_names: str = text("alternativeNames")
    is_wildcard: bool = boolean("isWildcard")
    is_san: bool = boolean("isSan")


@dataclass
class SSLOperationResult(Model):
    """The API's answer to a certificate operation."""

    success: bool = boolean("success")
    message: str = text("message")
    #: The id of the certificate. Store it: every later call for the certificate takes it.
    #: After ``ssl.renew`` it is the id of the **new** renewal certificate.
    certificate_id: str = text("certificateId")
    status: str = text("status")
    #: How to complete domain control validation (e.g. the CNAME record or file to create).
    dcv_details: str = text("dcvDetails")
    csr: str = text("csr")
    private_key: str = text("privateKey")


@dataclass
class CertificateStatus(Model):
    """The current state of a certificate."""

    certificate_id: str = text("certificateId")
    domain_name: str = text("domainName")
    status: str = text("status")
    status_message: str = text("statusMessage")
    is_configured: bool = boolean("isConfigured")
    is_issued: bool = boolean("isIssued")
    expires_at: Optional[datetime] = timestamp("certificateExpiresAt")


@dataclass
class CertificateSubscription(Model):
    """When a certificate was bought and when the subscription ends."""

    purchased_at: Optional[datetime] = timestamp("purchasedAt")
    expires_at: Optional[datetime] = timestamp("expiresAt")


@dataclass
class CertificateConfiguration(Model):
    """How a certificate was configured: CSR, validation method and approver."""

    configured_at: Optional[datetime] = timestamp("configuredAt")
    configuration_link: str = text("configurationLink")
    pin: str = text("pin")
    web_server: str = text("webServer")
    authentication_type: str = text("authenticationType")
    san_list: str = text("sanList")
    wildcard_list: str = text("wildcardList")
    approver_mail: str = text("approverMail")
    csr: str = text("csr")
    dcv_details: str = text("dcvDetails")


@dataclass
class CertificateIssue(Model):
    """When a certificate was issued and until when it is valid."""

    issued_at: Optional[datetime] = timestamp("issuedAt")
    valid_until: Optional[datetime] = timestamp("validUntil")


@dataclass
class Certificate(Model):
    """The full record of a certificate."""

    certificate_id: str = text("certificateId")
    domain_name: str = text("domainName")
    status: str = text("status")
    is_configured: bool = boolean("isConfigured")
    is_issued: bool = boolean("isIssued")
    package_name: str = text("packageName")
    package_code: str = text("packageCode")
    #: The paid term. ``subscription.expires_at`` decides when :meth:`SSLService.renew` is allowed.
    subscription: CertificateSubscription = model("subscription", CertificateSubscription)
    configuration: CertificateConfiguration = model("configuration", CertificateConfiguration)
    issued: CertificateIssue = model("certificate", CertificateIssue)
    contacts: List[SSLContact] = model_list("contacts", SSLContact)


@dataclass
class CertificateListItem(Model):
    """One certificate of the list: enough to find its ``certificate_id`` and see its state."""

    #: Pass it to the other ``client.ssl`` methods.
    certificate_id: str = text("certificateId")
    domain_name: str = text("domainName")
    package_code: str = text("packageCode")
    package_name: str = text("packageName")
    #: The API's status name, e.g. ``"Active"``, ``"WaitingForInstall"`` or ``"Renewed"``.
    status: str = text("status")
    #: Why the certificate has this status, e.g. ``"None"`` or ``"ConfigurationWindowExpired"``.
    status_reason: str = text("statusReason")
    is_configured: bool = boolean("isConfigured")
    is_issued: bool = boolean("isIssued")
    purchased_at: Optional[datetime] = timestamp("purchasedAt")
    #: The end of the paid term.
    subscription_expires_at: Optional[datetime] = timestamp("subscriptionExpiresAt")
    #: The end of the certificate's technical validity; ``None`` until it is issued.
    certificate_expires_at: Optional[datetime] = timestamp("certificateExpiresAt")
    #: On a renewal: the id of the certificate it renews. ``""`` otherwise.
    renewed_from_certificate_id: str = text("renewedFromCertificateId")


@dataclass
class CertificateContent(Model):
    """An issued certificate and its chain, PEM-encoded."""

    certificate_id: str = text("certificateId")
    certificate: str = text("certificate")
    intermediate1: str = text("intermediateCertificate1")
    intermediate2: str = text("intermediateCertificate2")
    root: str = text("rootCertificate")

    @property
    def chain(self) -> str:
        """The certificate followed by its intermediates, the bundle most web servers want."""
        parts = [p.strip() for p in (self.certificate, self.intermediate1, self.intermediate2) if p and p.strip()]
        return "\n".join(parts) + "\n"


@dataclass
class _Approvers(Model):
    mails: List[str] = texts("mails")


# ---------------------------------------------------------------------------
# Requests

_GUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)

_NOT_A_CERTIFICATE_ID = (
    "must be a certificate id (GUID), got %r. Certificates are no longer addressed by domain name: use the "
    "certificate_id returned by ssl.initialize or ssl.renew, or look it up with "
    "client.ssl.list(domain_name=...)")


def _certificate_id(value: Any) -> str:
    """The certificate id as it is sent: trimmed text (a ``uuid.UUID`` is accepted too)."""
    return "" if value is None else str(value).strip()


def _check_certificate_id(v: Validator, value: Any) -> bool:
    """The value must be a GUID. Catches a domain name passed where the API now wants a certificate id."""
    cert_id = _certificate_id(value)
    if not v.required("certificate_id", cert_id):
        return False
    return v.check(_GUID_RE.fullmatch(cert_id), "certificate_id", _NOT_A_CERTIFICATE_ID % cert_id)


def _certificate_body(certificate_id: Any) -> Body:
    """The body of the requests that only name a certificate."""
    return Body(certificateId=_certificate_id(certificate_id))


def _certificate_query(certificate_id: Any) -> Query:
    return Query().text("CertificateId", _certificate_id(certificate_id))


@dataclass
class SSLGenerateCSRRequest(BaseRequest):
    """Generate a CSR and private key. CLI: ``dna ssl generate-csr``"""

    method = "POST"
    path = "/api/v1/ssls/generate-csr"
    safety = Safety.READ
    response = CSR

    domain_name: str = ""
    #: The 2-letter ISO code.
    country: str = ""
    state: str = ""
    locality: str = ""
    organization: str = ""
    organization_unit: str = ""
    #: Extra names (SAN).
    alternative_names: List[str] = field(default_factory=list)

    def body(self) -> Body:
        return Body(domainName=strip(self.domain_name), country=strip(self.country).upper(), state=strip(self.state),
                    locality=strip(self.locality), organization=strip(self.organization),
                    organizationUnit=strip(self.organization_unit)).set(
            "alternativeNames", non_blank(self.alternative_names))

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)
        v.max_length("domain_name", strip(self.domain_name), 72)
        if v.required("country", self.country):
            v.check(len(strip(self.country)) == 2, "country", "must be a 2-letter ISO code")
        v.required("state", self.state)
        v.required("locality", self.locality)
        v.required("organization", self.organization)
        v.required("organization_unit", self.organization_unit)


@dataclass
class SSLCheckCSRRequest(BaseRequest):
    """Decode a CSR. CLI: ``dna ssl check-csr``"""

    method = "POST"
    path = "/api/v1/ssls/check-csr"
    safety = Safety.READ
    response = CSRInfo

    #: PEM-encoded.
    csr: str = ""

    def body(self) -> dict:
        return {"csr": strip(self.csr)}

    def validate(self, v: Validator) -> None:
        v.required("csr", self.csr)


@dataclass
class SSLInitializeRequest(BaseRequest):
    """Buy a certificate package for a domain. **Charges your balance.** CLI: ``dna ssl initialize``

    The answer's ``certificate_id`` identifies the new certificate in every later call.
    """

    method = "POST"
    path = "/api/v1/ssls/initialize"
    safety = Safety.BILLABLE
    response = SSLOperationResult

    domain_name: str = ""
    #: ``SSLProduct.product_code`` from ``client.products.ssls()``.
    package_code: str = ""

    def body(self) -> dict:
        return {"domainName": strip(self.domain_name), "packageCode": strip(self.package_code)}

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)
        v.required("package_code", self.package_code)


@dataclass
class SSLRenewRequest(BaseRequest):
    """Renew a certificate. **Charges your balance** (the renewal price). CLI: ``dna ssl renew``

    The answer's ``certificate_id`` is the id of the **new** renewal certificate,
    which must then be configured (:class:`SSLConfigureRequest`). Allowed from
    30 days before the subscription ends.
    """

    method = "POST"
    path = "/api/v1/ssls/renew"
    safety = Safety.BILLABLE
    response = SSLOperationResult

    #: The certificate to renew.
    certificate_id: str = ""

    def body(self) -> Body:
        return _certificate_body(self.certificate_id)

    def validate(self, v: Validator) -> None:
        _check_certificate_id(v, self.certificate_id)


@dataclass
class SSLConfigureRequest(BaseRequest):
    """Submit the CSR, validation method and contact of a certificate for issuance.

    The certificate must be waiting for configuration: within 15 days of
    ``initialize`` or ``renew``. CLI: ``dna ssl configure``
    """

    method = "PUT"
    path = "/api/v1/ssls/configure"
    safety = Safety.WRITE
    response = SSLOperationResult

    #: The id ``initialize`` or ``renew`` returned.
    certificate_id: str = ""
    #: PEM-encoded. Its common name must match the certificate's domain.
    csr: str = ""
    contact: SSLContact = field(default_factory=SSLContact)
    #: PEM-encoded; optional when the CSR was made elsewhere.
    private_key: str = ""
    #: Receives the approval e-mail (``AuthenticationType.EMAIL``); ``ssl.approvers`` lists the allowed ones.
    approver_mail: str = ""
    authentication_type: Optional[Union[AuthenticationType, str]] = None
    web_server_type: Optional[Union[WebServerType, str]] = None
    #: Additional names.
    san_list: List[str] = field(default_factory=list)
    wildcard_list: List[str] = field(default_factory=list)

    def body(self) -> Body:
        return (Body(certificateId=_certificate_id(self.certificate_id), csr=strip(self.csr),
                     contact=self.contact.to_api())
                .set("privateKey", self.private_key)
                .set("approverMail", self.approver_mail)
                .set("authenticationType", _enum_text(AuthenticationType, self.authentication_type))
                .set("webServerType", _enum_text(WebServerType, self.web_server_type))
                .set("sanList", ",".join(non_blank(self.san_list)))
                .set("wildcardList", ",".join(non_blank(self.wildcard_list))))

    def validate(self, v: Validator) -> None:
        _check_certificate_id(v, self.certificate_id)
        v.required("csr", self.csr)
        v.check(not self.approver_mail or "@" in self.approver_mail, "approver_mail", "is not an e-mail address")
        if self.authentication_type:
            _check_enum(v, "authentication_type", AuthenticationType, self.authentication_type)
        if self.web_server_type:
            _check_enum(v, "web_server_type", WebServerType, self.web_server_type)
        self.contact.validate(v)


def _enum_text(enum_cls: Any, value: Any) -> str:
    if not value:
        return ""
    try:
        return enum_cls.parse(value).value
    except ValueError:
        return strip(str(value))


def _check_enum(v: Validator, name: str, enum_cls: Any, value: Any) -> None:
    try:
        enum_cls.parse(value)
    except ValueError as err:
        v.add(name, str(err))


@dataclass
class SSLStatusRequest(BaseRequest):
    """Refresh and read the state of a certificate. CLI: ``dna ssl status``"""

    method = "PUT"
    path = "/api/v1/ssls/check-status"
    safety = Safety.READ
    response = CertificateStatus

    certificate_id: str = ""

    def body(self) -> Body:
        return _certificate_body(self.certificate_id)

    def validate(self, v: Validator) -> None:
        _check_certificate_id(v, self.certificate_id)


@dataclass
class SSLGetRequest(BaseRequest):
    """Read the full record of a certificate. CLI: ``dna ssl get``"""

    method = "GET"
    path = "/api/v1/ssls/certificate"
    safety = Safety.READ
    response = Certificate

    certificate_id: str = ""

    def query(self) -> Query:
        return _certificate_query(self.certificate_id)

    def validate(self, v: Validator) -> None:
        _check_certificate_id(v, self.certificate_id)


@dataclass
class SSLContentRequest(BaseRequest):
    """Download an issued certificate. CLI: ``dna ssl content``"""

    method = "GET"
    path = "/api/v1/ssls/certificate-content"
    safety = Safety.READ
    response = CertificateContent

    certificate_id: str = ""

    def query(self) -> Query:
        return _certificate_query(self.certificate_id)

    def validate(self, v: Validator) -> None:
        _check_certificate_id(v, self.certificate_id)


@dataclass
class SSLListRequest(BaseRequest):
    """List your certificates, newest first. CLI: ``dna ssl list``"""

    method = "GET"
    path = "/api/v1/ssls"
    safety = Safety.READ
    response = page_of(CertificateListItem)

    #: Keep only the certificates of this domain. For a wildcard certificate
    #: both ``"*.example.com"`` and ``"example.com"`` match.
    domain_name: str = ""
    skip: int = 0
    #: The page size; the API's default is 10 and its maximum 1000.
    limit: int = 0

    def query(self) -> Query:
        return Query().text("DomainName", self.domain_name).page(self.skip, self.limit)

    def validate(self, v: Validator) -> None:
        validate_paging(v, self.skip, self.limit)


@dataclass
class SSLReissueRequest(BaseRequest):
    """Reissue a certificate with a new CSR, key or approver. CLI: ``dna ssl reissue``"""

    method = "POST"
    path = "/api/v1/ssls/reissue"
    safety = Safety.WRITE
    response = SSLOperationResult

    certificate_id: str = ""
    approver_mail: str = ""
    csr: str = ""
    private_key: str = ""

    def body(self) -> Body:
        return (_certificate_body(self.certificate_id).set("approverMail", self.approver_mail)
                .set("csr", self.csr).set("privateKey", self.private_key))

    def validate(self, v: Validator) -> None:
        _check_certificate_id(v, self.certificate_id)


@dataclass
class SSLApproversRequest(BaseRequest):
    """List the e-mail addresses allowed for e-mail validation. CLI: ``dna ssl approvers``

    Set either ``certificate_id`` (an existing certificate: its domain and
    package are used, and the API ignores the other two fields), or
    ``domain_name`` and ``package_code`` (before a purchase).
    """

    method = "GET"
    path = "/api/v1/ssls/approvers"
    safety = Safety.READ
    response = _Approvers

    #: An existing certificate.
    certificate_id: str = ""
    #: The domain you are about to buy a certificate for; needs ``package_code``.
    domain_name: str = ""
    #: The package you are about to buy: ``SSLProduct.product_code``.
    package_code: str = ""

    def query(self) -> Query:
        return (_certificate_query(self.certificate_id).text("DomainName", self.domain_name)
                .text("PackageCode", self.package_code))

    def validate(self, v: Validator) -> None:
        if _certificate_id(self.certificate_id):
            _check_certificate_id(v, self.certificate_id)
        elif strip(self.domain_name):
            v.check(strip(self.package_code), "package_code",
                    "is required with domain_name: the approvers of a domain depend on the package you are "
                    "about to buy (for an existing certificate pass certificate_id instead)")
        else:
            v.add("certificate_id", "pass certificate_id (an existing certificate), or domain_name and "
                                    "package_code (before a purchase)")


@dataclass
class SSLRevokeRequest(BaseRequest):
    """Revoke a certificate. **This cannot be undone.** CLI: ``dna ssl revoke``"""

    method = "DELETE"
    path = "/api/v1/ssls/revoke"
    safety = Safety.DESTRUCTIVE
    response = SSLOperationResult

    certificate_id: str = ""

    def query(self) -> Query:
        return _certificate_query(self.certificate_id)

    def validate(self, v: Validator) -> None:
        _check_certificate_id(v, self.certificate_id)


# ---------------------------------------------------------------------------
# Service


class SSLService(Service):
    """SSL certificates. CLI: ``dna ssl``"""

    __slots__ = ()

    def generate_csr(self, domain_name: str, *, country: str, state: str, locality: str, organization: str,
                     organization_unit: str, alternative_names: Optional[Iterable[str]] = None) -> CSR:
        """A new CSR and its private key."""
        return self._send(SSLGenerateCSRRequest(domain_name, country, state, locality, organization,
                                                organization_unit, as_list(alternative_names)))

    def check_csr(self, csr: str) -> CSRInfo:
        """Decode a PEM-encoded CSR."""
        return self._send(SSLCheckCSRRequest(csr))

    def initialize(self, domain_name: str, package_code: str) -> SSLOperationResult:
        """Buy a certificate package for a domain. **Charges your balance.**

        Store ``result.certificate_id``: every later call for this certificate
        takes it. Then call :meth:`configure` within 15 days; after that the
        certificate is cancelled.
        """
        return self._operation(SSLInitializeRequest(domain_name, package_code))

    def renew(self, certificate_id: str) -> SSLOperationResult:
        """Renew a certificate for another year. **Charges your balance** (the renewal price).

        ``result.certificate_id`` is the id of the **new** renewal certificate,
        not the one you passed: :meth:`configure` it within 15 days (new CSR,
        contact and validation) and poll :meth:`status` with it. The old
        certificate keeps its id and stays valid until it expires.

        Allowed from 30 days before ``get(certificate_id).subscription.expires_at``.
        Do not renew with :meth:`initialize`: that buys an unrelated certificate
        at the purchase price. After a network error check :meth:`list` before
        trying again.
        """
        return self._operation(SSLRenewRequest(certificate_id))

    def configure(self, certificate_id: str, *, csr: str, contact: SSLContact, private_key: str = "",
                  approver_mail: str = "", authentication_type: Optional[Union[AuthenticationType, str]] = None,
                  web_server_type: Optional[Union[WebServerType, str]] = None,
                  san_list: Optional[Iterable[str]] = None,
                  wildcard_list: Optional[Iterable[str]] = None) -> SSLOperationResult:
        """Submit the CSR, validation method and contact of the certificate :meth:`initialize` or
        :meth:`renew` returned. Then poll :meth:`status` until ``is_issued``.

        The common name of the CSR must match the certificate's domain.
        """
        return self._operation(SSLConfigureRequest(certificate_id, csr, contact, private_key, approver_mail,
                                                   authentication_type, web_server_type, as_list(san_list),
                                                   as_list(wildcard_list)))

    def status(self, certificate_id: str) -> CertificateStatus:
        """Refresh and return the state of a certificate."""
        return self._send(SSLStatusRequest(certificate_id))

    def get(self, certificate_id: str) -> Certificate:
        """The full record of a certificate: subscription, configuration and contacts."""
        return self._send(SSLGetRequest(certificate_id))

    def content(self, certificate_id: str) -> CertificateContent:
        """The issued certificate and its chain."""
        return self._send(SSLContentRequest(certificate_id))

    def list(self, *, domain_name: str = "", skip: int = 0, limit: int = 0) -> Page[CertificateListItem]:
        """One page of your certificates, newest first.

        ``domain_name`` keeps only the certificates of one domain; use it to
        find a ``certificate_id``::

            for c in client.ssl.list(domain_name="example.com"):
                print(c.certificate_id, c.status, c.subscription_expires_at)
        """
        return self._send(SSLListRequest(domain_name, skip, limit))

    def all(self, *, domain_name: str = "", page_size: int = 100) -> Iterator[CertificateListItem]:
        """Every matching certificate, newest first; pages are fetched as you iterate."""
        return paginate(lambda skip, limit: self.list(domain_name=domain_name, skip=skip, limit=limit), 0,
                        page_size)

    def reissue(self, certificate_id: str, *, approver_mail: str = "", csr: str = "",
                private_key: str = "") -> SSLOperationResult:
        """Reissue a certificate with a new CSR, key or approver."""
        return self._operation(SSLReissueRequest(certificate_id, approver_mail, csr, private_key))

    def approvers(self, *, certificate_id: str = "", domain_name: str = "", package_code: str = "") -> List[str]:
        """The e-mail addresses allowed for e-mail validation.

        For an existing certificate pass ``certificate_id``; before a purchase
        pass ``domain_name`` and ``package_code``::

            client.ssl.approvers(certificate_id=order.certificate_id)
            client.ssl.approvers(domain_name="example.com", package_code="PositiveSSL")
        """
        res = self._send(SSLApproversRequest(certificate_id, domain_name, package_code))
        return res.mails if res is not None else []

    def revoke(self, certificate_id: str) -> SSLOperationResult:
        """Revoke a certificate. **This cannot be undone.**"""
        return self._operation(SSLRevokeRequest(certificate_id))

    def _operation(self, req: BaseRequest) -> SSLOperationResult:
        resp = self._exchange(req)
        res: SSLOperationResult = resp.value
        if res is None or not res.success:
            raise self._failed(req, resp, "", res.message if res is not None else "")
        return res
