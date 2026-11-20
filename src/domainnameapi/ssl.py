"""SSL certificates. CLI: ``dna ssl ...``

The flow: find a package with ``client.products.ssls()``, :meth:`~SSLService.generate_csr`
(or bring your own), :meth:`~SSLService.initialize` (charges the balance),
:meth:`~SSLService.configure`, then poll :meth:`~SSLService.status` until the
certificate is issued and download it with :meth:`~SSLService.content`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Union

from ._service import Service
from .contacts import digits
from .enums import AuthenticationType, WebServerType
from .model import Model, boolean, model, model_list, text, texts, timestamp
from .request import BaseRequest, Body, Query, Safety, Validator, as_list, domain_body, non_blank, strip

__all__ = [
    "CSR",
    "CSRInfo",
    "Certificate",
    "CertificateConfiguration",
    "CertificateContent",
    "CertificateIssue",
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
    "SSLOperationResult",
    "SSLReissueRequest",
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
    certificate_id: str = text("certificateId")
    status: str = text("status")
    #: How to complete domain control validation (e.g. the CNAME record or file to create).
    dcv_details: str = text("dcvDetails")
    csr: str = text("csr")
    private_key: str = text("privateKey")


@dataclass
class CertificateStatus(Model):
    """The current state of a certificate."""

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

    domain_name: str = text("domainName")
    status: str = text("status")
    is_configured: bool = boolean("isConfigured")
    is_issued: bool = boolean("isIssued")
    package_name: str = text("packageName")
    package_code: str = text("packageCode")
    subscription: CertificateSubscription = model("subscription", CertificateSubscription)
    configuration: CertificateConfiguration = model("configuration", CertificateConfiguration)
    issued: CertificateIssue = model("certificate", CertificateIssue)
    contacts: List[SSLContact] = model_list("contacts", SSLContact)


@dataclass
class CertificateContent(Model):
    """An issued certificate and its chain, PEM-encoded."""

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
    """Buy a certificate package for a domain. **Charges your balance.** CLI: ``dna ssl initialize``"""

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
class SSLConfigureRequest(BaseRequest):
    """Submit the CSR, validation method and contact of a certificate for issuance.

    CLI: ``dna ssl configure``
    """

    method = "PUT"
    path = "/api/v1/ssls/configure"
    safety = Safety.WRITE
    response = SSLOperationResult

    domain_name: str = ""
    #: PEM-encoded.
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
        return (Body(domainName=strip(self.domain_name), csr=strip(self.csr), contact=self.contact.to_api())
                .set("privateKey", self.private_key)
                .set("approverMail", self.approver_mail)
                .set("authenticationType", _enum_text(AuthenticationType, self.authentication_type))
                .set("webServerType", _enum_text(WebServerType, self.web_server_type))
                .set("sanList", ",".join(non_blank(self.san_list)))
                .set("wildcardList", ",".join(non_blank(self.wildcard_list))))

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)
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

    domain_name: str = ""

    def body(self) -> Body:
        return domain_body(self.domain_name)

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)


@dataclass
class SSLGetRequest(BaseRequest):
    """Read the full record of a certificate. CLI: ``dna ssl get``"""

    method = "GET"
    path = "/api/v1/ssls/certificate"
    safety = Safety.READ
    response = Certificate

    domain_name: str = ""

    def query(self) -> Query:
        return Query().text("DomainName", self.domain_name)

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)


@dataclass
class SSLContentRequest(BaseRequest):
    """Download an issued certificate. CLI: ``dna ssl content``"""

    method = "GET"
    path = "/api/v1/ssls/certificate-content"
    safety = Safety.READ
    response = CertificateContent

    domain_name: str = ""

    def query(self) -> Query:
        return Query().text("DomainName", self.domain_name)

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)


@dataclass
class SSLReissueRequest(BaseRequest):
    """Reissue a certificate with a new CSR, key or approver. CLI: ``dna ssl reissue``"""

    method = "POST"
    path = "/api/v1/ssls/reissue"
    safety = Safety.WRITE
    response = SSLOperationResult

    domain_name: str = ""
    approver_mail: str = ""
    csr: str = ""
    private_key: str = ""

    def body(self) -> Body:
        return (domain_body(self.domain_name).set("approverMail", self.approver_mail).set("csr", self.csr)
                .set("privateKey", self.private_key))

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)


@dataclass
class SSLApproversRequest(BaseRequest):
    """List the e-mail addresses allowed for e-mail validation. CLI: ``dna ssl approvers``"""

    method = "GET"
    path = "/api/v1/ssls/approvers"
    safety = Safety.READ
    response = _Approvers

    domain_name: str = ""
    #: Narrows the list to a package; optional.
    package_code: str = ""

    def query(self) -> Query:
        return Query().text("DomainName", self.domain_name).text("PackageCode", self.package_code)

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)


@dataclass
class SSLRevokeRequest(BaseRequest):
    """Revoke a certificate. **This cannot be undone.** CLI: ``dna ssl revoke``"""

    method = "DELETE"
    path = "/api/v1/ssls/revoke"
    safety = Safety.DESTRUCTIVE
    response = SSLOperationResult

    domain_name: str = ""

    def query(self) -> Query:
        return Query().text("DomainName", self.domain_name)

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)


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
        """Buy a certificate package for a domain. **Charges your balance.** Then call :meth:`configure`."""
        return self._operation(SSLInitializeRequest(domain_name, package_code))

    def configure(self, domain_name: str, *, csr: str, contact: SSLContact, private_key: str = "",
                  approver_mail: str = "", authentication_type: Optional[Union[AuthenticationType, str]] = None,
                  web_server_type: Optional[Union[WebServerType, str]] = None,
                  san_list: Optional[Iterable[str]] = None,
                  wildcard_list: Optional[Iterable[str]] = None) -> SSLOperationResult:
        """Submit the CSR, validation method and contact. Then poll :meth:`status` until ``is_issued``."""
        return self._operation(SSLConfigureRequest(domain_name, csr, contact, private_key, approver_mail,
                                                   authentication_type, web_server_type, as_list(san_list),
                                                   as_list(wildcard_list)))

    def status(self, domain_name: str) -> CertificateStatus:
        """Refresh and return the state of a certificate."""
        return self._send(SSLStatusRequest(domain_name))

    def get(self, domain_name: str) -> Certificate:
        """The full record of a certificate: subscription, configuration and contacts."""
        return self._send(SSLGetRequest(domain_name))

    def content(self, domain_name: str) -> CertificateContent:
        """The issued certificate and its chain."""
        return self._send(SSLContentRequest(domain_name))

    def reissue(self, domain_name: str, *, approver_mail: str = "", csr: str = "",
                private_key: str = "") -> SSLOperationResult:
        """Reissue a certificate with a new CSR, key or approver."""
        return self._operation(SSLReissueRequest(domain_name, approver_mail, csr, private_key))

    def approvers(self, domain_name: str, package_code: str = "") -> List[str]:
        """The e-mail addresses allowed for e-mail validation."""
        res = self._send(SSLApproversRequest(domain_name, package_code))
        return res.mails if res is not None else []

    def revoke(self, domain_name: str) -> SSLOperationResult:
        """Revoke a certificate. **This cannot be undone.**"""
        return self._operation(SSLRevokeRequest(domain_name))

    def _operation(self, req: BaseRequest) -> SSLOperationResult:
        resp = self._exchange(req)
        res: SSLOperationResult = resp.value
        if res is None or not res.success:
            raise self._failed(req, resp, "", res.message if res is not None else "")
        return res
