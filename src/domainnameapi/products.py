"""The catalogue: TLDs, SSL certificates and other products with your prices. CLI: ``dna product ...``"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, List, Optional, Union

from ._service import Service
from .enums import OrderType, ProductType
from .model import (
    Model,
    Page,
    boolean,
    enum_value,
    integer,
    integers,
    model_list,
    number,
    optional_model,
    page_of,
    paginate,
    text,
)
from .request import BaseRequest, Query, Safety, Validator, parse_enum, strip, validate_paging

__all__ = [
    "Price",
    "Product",
    "ProductInfo",
    "ProductInfoRequest",
    "ProductListRequest",
    "ProductService",
    "SSLPriceGroup",
    "SSLProduct",
    "SSLProductListRequest",
    "Subproduct",
    "TLD",
    "TLDAttribute",
    "TLDAttributeOption",
    "TLDListRequest",
    "TLDPriceGroup",
]


# ---------------------------------------------------------------------------
# Models


@dataclass
class Price(Model):
    """The price of a product for one period."""

    #: The number of years.
    period: int = integer("period")
    price: float = number("price")
    #: The ISO 4217 code, e.g. ``"USD"``.
    currency: str = text("currency")

    def __str__(self) -> str:
        return ("%.2f %s" % (self.price, self.currency)).strip()


@dataclass
class Product(Model):
    """A product of the catalogue."""

    id: str = text("id")
    parent_product_id: str = text("parentProductId")
    name: str = text("productName")
    product_code: str = text("productCode")
    entity_id: str = text("entityId")
    product_type: Optional[ProductType] = enum_value("productType", ProductType)


@dataclass
class Subproduct(Model):
    """A part of a product price, with buying and selling price."""

    parent_product_id: str = text("parentProductId")
    name: str = text("productName")
    product_code: str = text("productCode")
    product_type: Optional[ProductType] = enum_value("productType", ProductType)
    entity_id: str = text("entityId")
    buying_price: float = number("buyingPrice")
    buying_currency: str = text("buyingCurrency")
    selling_price: float = number("sellingPrice")
    selling_currency: str = text("sellingCurrency")


@dataclass
class ProductInfo(Model):
    """The price of a product for one order type and period."""

    parent_product_id: str = text("parentProductId")
    name: str = text("productName")
    product_code: str = text("productCode")
    entity_id: str = text("entityId")
    product_type: Optional[ProductType] = enum_value("productType", ProductType)
    selling_price: float = number("sellingPrice")
    selling_currency: str = text("sellingCurrency")
    subproducts: List[Subproduct] = model_list("subproducts", Subproduct)


@dataclass
class TLDPriceGroup(Model):
    """The prices of one price group."""

    price_group: str = text("priceGroup")
    register: List[Price] = model_list("register", Price)
    renew: List[Price] = model_list("renew", Price)
    transfer: List[Price] = model_list("transfer", Price)
    restore: Optional[Price] = optional_model("restore", Price)
    refund: Optional[Price] = optional_model("refund", Price)
    backorder: Optional[Price] = optional_model("backorder", Price)


@dataclass
class TLDAttributeOption(Model):
    """An allowed value of a TLD attribute."""

    value: str = text("value")


@dataclass
class TLDAttribute(Model):
    """A registry attribute of a TLD."""

    key: str = text("key")
    description: str = text("description")
    required: bool = boolean("isRequired")
    type: str = text("type")
    options: List[TLDAttributeOption] = model_list("options", TLDAttributeOption)


@dataclass
class TLD(Model):
    """A top-level domain you can sell: prices, periods, rules and the registry attributes it needs."""

    #: The TLD without the leading dot, e.g. ``"com"`` or ``"com.tr"``.
    name: str = text("name")
    min_registration_period: int = integer("minRegistrationPeriod")
    max_registration_period: int = integer("maxRegistrationPeriod")
    registration_periods: List[int] = integers("registrationPeriods")
    renewal_periods: List[int] = integers("renewalPeriods")
    # Grace and lifecycle periods, in days.
    add_grace_period: int = integer("addGracePeriod")
    auto_renew_grace_period: int = integer("autoRenewGracePeriod")
    finalization_period: int = integer("finalizationPeriod")
    failure_period: int = integer("failurePeriod")
    payment_period: int = integer("paymentPeriod")
    deletion_restorable_period: int = integer("deletionRestorablePeriod")
    deletion_hold_period: int = integer("deletionHoldPeriod")
    transfer_period: int = integer("transferPeriod")
    register_period: int = integer("registerPeriod")
    renewal_period: int = integer("renewalPeriod")
    # Capabilities.
    is_support_transfer: bool = boolean("isSupportTransfer")
    is_support_idn: bool = boolean("isSupportIdn")
    is_require_document: bool = boolean("isRequireDocument")
    is_support_trustee: bool = boolean("isSupportTrustee")
    is_trustee_required: bool = boolean("isTrusteeRequired")
    is_sale_allowed: bool = boolean("isSaleAllowed")
    is_transfer_lock_possible: bool = boolean("isTransferLockPossible")
    is_handle_update_available: bool = boolean("isHandleUpdateAvailable")
    is_privacy_available: bool = boolean("isPrivacyAvailable")
    is_dnssec_available: bool = boolean("isDnssecAvailable")
    is_ipv6_available: bool = boolean("isIpv6Available")
    is_explicit_renewal_supported: bool = boolean("isExplicitRenewalSupported")
    available_in_test_environment: bool = boolean("availableInTestEnvironment")
    is_required_auth_code: bool = boolean("isRequiredAuthCode")
    registry_dns_check: bool = boolean("registryDnsCheck")
    is_transfer_check_supported: bool = boolean("isTransferCheckSupported")
    is_glue_record_allowed: bool = boolean("isGlueRecordAllowed")
    is_host_object_accepted: bool = boolean("isHostObjectAccepted")
    prices: List[TLDPriceGroup] = model_list("prices", TLDPriceGroup)
    #: The registry attributes of the TLD; pass the required ones as ``tld_attributes`` when registering.
    attributes: List[TLDAttribute] = model_list("attributes", TLDAttribute)

    def register_price(self, years: int) -> Optional[Price]:
        """The registration price for a period in years, or ``None``."""
        return self._price("register", years)

    def renew_price(self, years: int) -> Optional[Price]:
        """The renewal price for a period in years, or ``None``."""
        return self._price("renew", years)

    def transfer_price(self, years: int) -> Optional[Price]:
        """The transfer price for a period in years, or ``None``."""
        return self._price("transfer", years)

    def _price(self, kind: str, years: int) -> Optional[Price]:
        for group in self.prices:
            for p in getattr(group, kind):
                if p.period == years:
                    return p
        return None

    @property
    def required_attributes(self) -> List[TLDAttribute]:
        """The attributes a registration must include."""
        return [a for a in self.attributes if a.required]


@dataclass
class SSLPriceGroup(Model):
    """The prices of an SSL product in one price group."""

    price_group: str = text("priceGroup")
    create: List[Price] = model_list("create", Price)


@dataclass
class SSLProduct(Model):
    """An SSL certificate product."""

    name: str = text("name")
    #: The package code ``ssl.initialize`` takes.
    product_code: str = text("productCode")
    vendor_name: str = text("vendorName")
    validation_type: str = text("validationType")
    is_wildcard: bool = boolean("isWildcard")
    is_multi_domain: bool = boolean("isMultiDomain")
    default_san_count: int = integer("defaultSanCount")
    max_san_count: int = integer("maxSanCount")
    warranty_amount: float = number("warrantyAmount")
    issue_time_minutes: int = integer("issueTimeMinutes")
    is_reissue_free: bool = boolean("isReissueFree")
    requires_csr: bool = boolean("requiresCsr")
    prices: List[SSLPriceGroup] = model_list("prices", SSLPriceGroup)


# ---------------------------------------------------------------------------
# Requests


@dataclass
class ProductListRequest(BaseRequest):
    """List products. CLI: ``dna product list``"""

    method = "GET"
    path = "/api/v1/products"
    safety = Safety.READ
    response = page_of(Product)

    filter_text: str = ""
    #: ``None`` for all.
    product_type: Optional[Union[ProductType, int, str]] = None
    skip: int = 0
    limit: int = 0
    sort: str = ""

    def query(self) -> Query:
        kind = parse_enum(ProductType, self.product_type)
        return Query().text("FilterText", self.filter_text).number(
            "ProductType", int(kind) if kind is not None else 0).page(self.skip, self.limit, self.sort)

    def validate(self, v: Validator) -> None:
        validate_paging(v, self.skip, self.limit)
        v.enum("product_type", self.product_type, ProductType)


@dataclass
class ProductInfoRequest(BaseRequest):
    """Read the price of a product for an order type and period. CLI: ``dna product info``"""

    method = "GET"
    path = "/api/v1/products/info"
    safety = Safety.READ
    response = ProductInfo

    #: A TLD without the dot (``"com"``, ``"com.tr"``) or another product name.
    product_name: str = ""
    order_type: Optional[Union[OrderType, int, str]] = None
    #: The period.
    years: int = 0

    def query(self) -> Query:
        return (Query().text("ProductName", strip(self.product_name).lstrip("."))
                .always("OrderType", int(OrderType.parse(self.order_type)))
                .always("Period", self.years))

    def validate(self, v: Validator) -> None:
        v.required("product_name", self.product_name)
        v.enum("order_type", self.order_type, OrderType, optional=False)
        v.between("years", self.years, 1, 10, optional=False)


@dataclass
class TLDListRequest(BaseRequest):
    """List TLDs with prices and rules. CLI: ``dna product tlds``"""

    method = "GET"
    path = "/api/v1/products/tlds"
    safety = Safety.READ
    response = page_of(TLD)

    #: Keep TLDs matching this text, e.g. ``"com.tr"``.
    filter_text: str = ""
    #: The price currency; empty uses the client's or the account's.
    currency: str = ""
    skip: int = 0
    limit: int = 0
    sort: str = ""

    def query(self) -> Query:
        return Query().text("FilterText", self.filter_text).text("Currency", self.currency).page(
            self.skip, self.limit, self.sort)

    def validate(self, v: Validator) -> None:
        validate_paging(v, self.skip, self.limit)


@dataclass
class SSLProductListRequest(BaseRequest):
    """List SSL certificate products. CLI: ``dna product ssls``"""

    method = "GET"
    path = "/api/v1/products/ssls"
    safety = Safety.READ
    response = page_of(SSLProduct)

    filter_text: str = ""
    vendor_name: str = ""
    #: The price currency; empty uses the client's or the account's.
    currency: str = ""
    #: The API's numeric validation type; 0 for all.
    validation_type: int = 0
    #: Filter when set.
    is_wildcard: Optional[bool] = None
    is_multi_domain: Optional[bool] = None
    skip: int = 0
    limit: int = 0
    sort: str = ""

    def query(self) -> Query:
        return (Query().text("FilterText", self.filter_text).text("VendorName", self.vendor_name)
                .text("Currency", self.currency).number("ValidationType", self.validation_type)
                .flag("IsWildcard", self.is_wildcard).flag("IsMultiDomain", self.is_multi_domain)
                .page(self.skip, self.limit, self.sort))

    def validate(self, v: Validator) -> None:
        validate_paging(v, self.skip, self.limit)


# ---------------------------------------------------------------------------
# Service


class ProductService(Service):
    """The catalogue and prices of TLDs, SSL and other products. CLI: ``dna product``"""

    __slots__ = ()

    def list(self, *, filter_text: str = "", product_type: Any = None, skip: int = 0, limit: int = 0,
             sort: str = "") -> Page[Product]:
        """One page of products."""
        return self._send(ProductListRequest(filter_text, product_type, skip, limit, sort))

    def info(self, product_name: str, order_type: Union[OrderType, int, str], years: int) -> ProductInfo:
        """The price of a product for an order type and period, e.g. a 2-year .com renewal::

            client.products.info("com", OrderType.RENEW, 2)
        """
        return self._send(ProductInfoRequest(product_name, order_type, years))

    def tlds(self, *, filter_text: str = "", currency: Optional[str] = None, skip: int = 0, limit: int = 0,
             sort: str = "") -> Page[TLD]:
        """One page of the TLD catalogue. Not rate limited; cache it rather than asking for every search."""
        cur = currency if currency is not None else self._client.currency
        return self._send(TLDListRequest(filter_text, cur, skip, limit, sort))

    def all_tlds(self, *, filter_text: str = "", currency: Optional[str] = None, sort: str = "",
                 page_size: int = 100) -> Iterator[TLD]:
        """The whole TLD catalogue; pages are fetched as you iterate."""
        return paginate(lambda skip, limit: self.tlds(filter_text=filter_text, currency=currency, skip=skip,
                                                      limit=limit, sort=sort), 0, page_size)

    def tld(self, name: str, *, currency: Optional[str] = None) -> Optional[TLD]:
        """One TLD by name (``"com.tr"`` or ``".com.tr"``), or ``None`` when the catalogue does not have it."""
        wanted = strip(name).lstrip(".").lower()
        for t in self.all_tlds(filter_text=wanted, currency=currency):
            if t.name.lower() == wanted:
                return t
        return None

    def ssls(self, *, filter_text: str = "", vendor_name: str = "", currency: Optional[str] = None,
             validation_type: int = 0, is_wildcard: Optional[bool] = None, is_multi_domain: Optional[bool] = None,
             skip: int = 0, limit: int = 0, sort: str = "") -> Page[SSLProduct]:
        """One page of SSL certificate products."""
        cur = currency if currency is not None else self._client.currency
        return self._send(SSLProductListRequest(filter_text, vendor_name, cur, validation_type, is_wildcard,
                                                is_multi_domain, skip, limit, sort))
