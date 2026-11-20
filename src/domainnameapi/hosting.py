"""Web hosting. CLI: ``dna hosting ...``

The flow: pick a plan from :meth:`~HostingService.packages`,
:meth:`~HostingService.create` (charges the balance; provisioning continues
after the call returns), then :meth:`~HostingService.wait` until the hosting
is active. Never create again for a hosting still provisioning: that charges twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from ._service import Service, first_text
from .errors import OperationError, WaitTimeoutError
from .model import Model, boolean, integer, list_of, model_list, optional_integer, text, timestamp
from .request import BaseRequest, Query, Safety, Validator, strip

__all__ = [
    "HOSTING_ACTIVE",
    "HOSTING_DELETED",
    "HOSTING_FAILED",
    "HOSTING_PROVISIONING",
    "HOSTING_SUSPENDED",
    "Hosting",
    "HostingCreateRequest",
    "HostingCreateResult",
    "HostingGetByTokenRequest",
    "HostingGetRequest",
    "HostingPackage",
    "HostingPackagesRequest",
    "HostingPlansRequest",
    "HostingService",
    "HostingStatus",
    "HostingStatusRequest",
    "PackagePlan",
    "ServicePlan",
]

# Provisioning states (HostingStatus.status, Hosting.status).
HOSTING_PROVISIONING = "Provisioning"
HOSTING_ACTIVE = "Active"
#: The balance is refunded automatically.
HOSTING_FAILED = "Failed"
HOSTING_SUSPENDED = "Suspended"
HOSTING_DELETED = "Deleted"


# ---------------------------------------------------------------------------
# Models


@dataclass
class PackagePlan(Model):
    """A service plan of a hosting package."""

    #: The value ``hosting.create`` takes.
    service_plan: str = text("servicePlan")
    #: Part of the plan; cannot be changed later.
    operating_system: str = text("operatingSystem")
    panel_type: str = text("panelType")


@dataclass
class HostingPackage(Model):
    """A hosting package and the plans it offers."""

    name: str = text("name")
    required_min_leasing: int = integer("requiredMinLeasing")
    permitted_max_leasing: int = integer("permittedMaxLeasing")
    service_plans: List[PackagePlan] = model_list("servicePlans", PackagePlan)


@dataclass
class ServicePlan(Model):
    """A hosting plan and its limits. ``None`` means unlimited, not zero."""

    name: str = text("name")
    external_id: str = text("externalId")
    disk_quota_mb: Optional[int] = optional_integer("diskQuotaMb")
    bandwidth_limit_mb: Optional[int] = optional_integer("bandwidthLimitMb")
    max_domains: Optional[int] = optional_integer("maxDomains")
    max_sub_domains: Optional[int] = optional_integer("maxSubDomains")
    max_databases: Optional[int] = optional_integer("maxDatabases")
    max_ftp_accounts: Optional[int] = optional_integer("maxFtpAccounts")
    max_email_accounts: Optional[int] = optional_integer("maxEmailAccounts")
    has_dedicated_ip: bool = boolean("hasDedicatedIp")
    has_shell_access: bool = boolean("hasShellAccess")


@dataclass
class HostingCreateResult(Model):
    """The API's answer to :class:`HostingCreateRequest`."""

    #: Identifies the hosting ("HST-..."); store it.
    service_id: str = text("serviceId")
    status: str = text("status")
    #: The panel access fields are empty until the hosting is active.
    panel_address: str = text("panelAddress")
    username: str = text("username")
    password: str = text("password")
    token: str = text("token")


@dataclass
class Hosting(Model):
    """A hosting service."""

    #: The UUID ``hosting.plans`` takes.
    hosting_id: str = text("hostingId")
    service_id: str = text("serviceId")
    domain_name: str = text("domainName")
    package_name: str = text("packageName")
    lease_on: Optional[datetime] = timestamp("leaseOn")
    expires_on: Optional[datetime] = timestamp("expiredOn")
    status: str = text("status")
    external_customer_id: str = text("externalCustomerId")


@dataclass
class HostingStatus(Model):
    """The provisioning state of a hosting. The panel access fields are set once it is active."""

    service_id: str = text("serviceId")
    domain_name: str = text("domainName")
    status: str = text("status")
    status_message: str = text("statusMessage")
    panel_address: str = text("panelAddress")
    username: str = text("username")
    password: str = text("password")
    token: str = text("token")
    failure_reason: str = text("failureReason")

    @property
    def active(self) -> bool:
        """``True`` when the hosting is ready to use."""
        return self.status.strip().lower() == HOSTING_ACTIVE.lower()

    @property
    def failed(self) -> bool:
        """``True`` when provisioning failed."""
        return self.status.strip().lower() == HOSTING_FAILED.lower()


# ---------------------------------------------------------------------------
# Requests


def _exactly_one(v: Validator, service_id: str, domain_name: str) -> None:
    v.check(bool(strip(service_id)) != bool(strip(domain_name)), "service_id",
            "set either the service ID or the domain name")


@dataclass
class HostingPackagesRequest(BaseRequest):
    """List hosting packages. CLI: ``dna hosting packages``"""

    method = "GET"
    path = "/api/v1/hostings/packages"
    safety = Safety.READ
    response = list_of(HostingPackage)


@dataclass
class HostingPlansRequest(BaseRequest):
    """List service plans and their limits. CLI: ``dna hosting plans``"""

    method = "GET"
    path = "/api/v1/hostings/plans"
    safety = Safety.READ
    response = list_of(ServicePlan)

    #: Limits the list to the plans of one hosting (``Hosting.hosting_id``); optional.
    hosting_id: str = ""

    def query(self) -> Query:
        return Query().text("hostingId", self.hosting_id)


@dataclass
class HostingCreateRequest(BaseRequest):
    """Order a hosting for a domain. **Charges your balance.** CLI: ``dna hosting create``"""

    method = "POST"
    path = "/api/v1/hostings/create"
    safety = Safety.BILLABLE
    response = HostingCreateResult

    domain_name: str = ""
    #: From ``hosting.packages()``.
    service_plan: str = ""

    def body(self) -> dict:
        return {"domainName": strip(self.domain_name), "servicePlan": strip(self.service_plan)}

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)
        v.required("service_plan", self.service_plan)


@dataclass
class HostingGetRequest(BaseRequest):
    """Read a hosting by service ID or domain name (set exactly one). CLI: ``dna hosting get``"""

    method = "GET"
    path = "/api/v1/hostings"
    safety = Safety.READ
    response = Hosting

    service_id: str = ""
    domain_name: str = ""

    def query(self) -> Query:
        return Query().text("serviceId", self.service_id).text("domainName", self.domain_name)

    def validate(self, v: Validator) -> None:
        _exactly_one(v, self.service_id, self.domain_name)


@dataclass
class HostingGetByTokenRequest(BaseRequest):
    """Read a hosting by the token ``create`` returned. CLI: ``dna hosting get-by-token``"""

    method = "GET"
    path = "/api/v1/hostings/by-token"
    safety = Safety.READ
    response = Hosting

    token: str = ""

    def query(self) -> Query:
        return Query().text("token", self.token)

    def validate(self, v: Validator) -> None:
        v.required("token", self.token)


@dataclass
class HostingStatusRequest(BaseRequest):
    """Read the provisioning state of a hosting by service ID (preferred) or domain name.

    Set exactly one. CLI: ``dna hosting status``
    """

    method = "GET"
    path = "/api/v1/hostings/check-status"
    safety = Safety.READ
    response = HostingStatus

    service_id: str = ""
    domain_name: str = ""

    def query(self) -> Query:
        return Query().text("ServiceId", self.service_id).text("DomainName", self.domain_name)

    def validate(self, v: Validator) -> None:
        _exactly_one(v, self.service_id, self.domain_name)


# ---------------------------------------------------------------------------
# Service


class HostingService(Service):
    """Web hosting packages and services. CLI: ``dna hosting``"""

    __slots__ = ()

    #: Poll intervals of :meth:`wait`: every 5 s for the first 2 minutes, then every 30 s.
    poll_fast = 5.0
    poll_slow = 30.0

    def packages(self) -> List[HostingPackage]:
        """The hosting packages and their service plans."""
        return self._send(HostingPackagesRequest()) or []

    def plans(self, hosting_id: str = "") -> List[ServicePlan]:
        """Service plans and their limits; ``hosting_id`` limits them to one hosting."""
        return self._send(HostingPlansRequest(hosting_id)) or []

    def create(self, domain_name: str, service_plan: str) -> HostingCreateResult:
        """Order a hosting. **Charges your balance.**

        Provisioning continues after the call returns: pass the result's
        ``service_id`` to :meth:`wait`.
        """
        return self._send(HostingCreateRequest(domain_name, service_plan))

    def get(self, *, service_id: str = "", domain_name: str = "") -> Hosting:
        """A hosting by service ID or domain name."""
        return self._send(HostingGetRequest(service_id, domain_name))

    def get_by_token(self, token: str) -> Hosting:
        """A hosting by the token :meth:`create` returned."""
        return self._send(HostingGetByTokenRequest(token))

    def status(self, *, service_id: str = "", domain_name: str = "") -> HostingStatus:
        """The provisioning state of a hosting."""
        return self._send(HostingStatusRequest(service_id, domain_name))

    def wait(self, service_id: str, *, timeout: float = 30 * 60) -> HostingStatus:
        """Poll :meth:`status` until the hosting is active and return its panel access.

        Polls every 5 seconds for 2 minutes, then every 30 seconds, for at most
        ``timeout`` seconds (default 30 minutes), then raises
        :class:`~domainnameapi.WaitTimeoutError`. A failed provisioning raises
        :class:`~domainnameapi.OperationError` with the failure reason::

            created = client.hosting.create("example.com", "Linux-Starter")
            st = client.hosting.wait(created.service_id)
            print(st.panel_address, st.username, st.password)
        """
        client = self._client
        req = HostingStatusRequest(service_id)
        start = client._clock()
        while True:
            st = self._send(req)
            if st.active:
                return st
            if st.failed:
                ep = req.endpoint()
                raise OperationError(ep.method, ep.path, HOSTING_FAILED,
                                     first_text(st.failure_reason, st.status_message, "hosting provisioning failed"))
            elapsed = client._clock() - start
            interval = self.poll_fast if elapsed < 120 else self.poll_slow
            if elapsed + interval > timeout:
                raise WaitTimeoutError("hosting %s is still %s after %ds" % (service_id, st.status or "pending",
                                                                            int(elapsed)), st)
            client._sleep(interval)

