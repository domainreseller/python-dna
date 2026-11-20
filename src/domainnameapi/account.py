"""The reseller account: balances and the balance ledger. CLI: ``dna account ...``"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator, List, Optional

from ._service import Service
from .enums import ChargeType, ProductType, TransactionStatus, TransactionType
from .model import Model, Page, enum_value, integer, number, page_of, paginate, text, timestamp
from .request import BaseRequest, Query, Safety, Validator, as_list, enum_values, parse_enum, validate_paging

__all__ = [
    "Account",
    "AccountGetRequest",
    "AccountService",
    "AccountTransactionsRequest",
    "Transaction",
]


# ---------------------------------------------------------------------------
# Models


@dataclass
class Account(Model):
    """The reseller account and its balances."""

    reseller_id: str = text("resellerId")
    reseller_name: str = text("resellerName")
    reseller_group_name: str = text("resellerGroupName")
    try_balance: float = number("tryBalance")
    usd_balance: float = number("usdBalance")

    def balance(self, currency: str) -> Optional[float]:
        """The balance in ``"USD"`` or ``"TRY"`` (any case, ``"TL"`` works too).

        ``None`` for other currencies: the account holds only these two.
        """
        code = (currency or "").strip().upper()
        if code == "USD":
            return self.usd_balance
        if code in ("TRY", "TL"):
            return self.try_balance
        return None


@dataclass
class Transaction(Model):
    """One entry of the balance ledger."""

    trace_id: str = text("traceId")
    type: Optional[TransactionType] = enum_value("type", TransactionType)
    status: Optional[TransactionStatus] = enum_value("status", TransactionStatus)
    charge_type: Optional[ChargeType] = enum_value("chargeType", ChargeType)
    amount: float = number("amount")
    amount_currency: str = text("amountCurrency")
    exchange_amount: float = number("exchangeAmount")
    #: Numeric in the API.
    exchange_currency: float = number("exchangeCurrency")
    product_type: Optional[ProductType] = enum_value("productType", ProductType)
    product_id: str = text("productId")
    description: str = text("description")
    #: The number of years bought, for domain transactions.
    period: int = integer("period")
    creation_time: Optional[datetime] = timestamp("creationTime")
    reseller_name: str = text("resellerName")
    #: The balance after the transaction.
    balance: float = number("balance")
    #: The balance before it.
    old_balance: float = number("oldBalance")

    @property
    def change(self) -> float:
        """How the transaction moved the balance: positive for credits, negative for charges.

        Reliable even when ``amount`` is 0.
        """
        return round(self.balance - self.old_balance, 2)


# ---------------------------------------------------------------------------
# Requests


@dataclass
class AccountGetRequest(BaseRequest):
    """Read the account. CLI: ``dna account get``"""

    method = "GET"
    path = "/api/v1/deposit/accounts/me"
    safety = Safety.READ
    response = Account


@dataclass
class AccountTransactionsRequest(BaseRequest):
    """List balance transactions. CLI: ``dna account transactions``"""

    method = "GET"
    path = "/api/v1/deposit/transactions"
    safety = Safety.READ
    response = page_of(Transaction)

    #: Keep only these kinds (Register, Renew, ...).
    transaction_types: Optional[List[Any]] = None
    #: Keep only these product kinds.
    product_types: Optional[List[Any]] = None
    #: Keep only credits (``ChargeType.ADD``) or debits (``ChargeType.SUBTRACT``).
    charge_type: Optional[Any] = None
    #: Keep only these currencies, e.g. ``["USD"]``.
    currencies: Optional[List[str]] = None
    #: Keep only transactions created at or after this time.
    since: Optional[datetime] = None
    #: Keep only transactions created at or before this time.
    until: Optional[datetime] = None
    #: Find one transaction.
    trace_id: str = ""
    #: Search the description.
    description: str = ""
    #: Search the text.
    filter_text: str = ""
    #: Keep only transactions of this amount.
    amount: float = 0.0
    skip: int = 0
    limit: int = 0
    #: A sort expression such as ``"creationTime desc"``.
    sort: str = ""

    def query(self) -> Query:
        q = (Query()
             .each("TransactionTypes", [int(t) for t in enum_values(TransactionType, self.transaction_types)])
             .each("ProductTypes", [int(t) for t in enum_values(ProductType, self.product_types)])
             .each("AccountCurrencyTypes", self.currencies)
             .date("StartDate", self.since)
             .date("EndDate", self.until)
             .text("TraceId", self.trace_id)
             .text("Description", self.description)
             .text("FilterText", self.filter_text)
             .number("Amount", self.amount)
             .page(self.skip, self.limit, self.sort))
        if self.charge_type is not None:
            q.always("ChargeType", int(parse_enum(ChargeType, self.charge_type)))
        return q

    def validate(self, v: Validator) -> None:
        validate_paging(v, self.skip, self.limit)
        for t in self.transaction_types or []:
            v.enum("transaction_types", t, TransactionType)
        for t in self.product_types or []:
            v.enum("product_types", t, ProductType)
        v.enum("charge_type", self.charge_type, ChargeType)
        if self.since is not None and self.until is not None:
            v.check(_comparable(self.until) >= _comparable(self.since), "until", "must not be before since")


def _comparable(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Service


class AccountService(Service):
    """The reseller account: balances and the balance ledger. CLI: ``dna account``"""

    __slots__ = ()

    def get(self) -> Account:
        """The account and its TRY and USD balances.

        Also the cheapest way to check that the credentials work.
        """
        return self._send(AccountGetRequest())

    def transactions(
        self,
        *,
        transaction_types: Optional[Iterable[Any]] = None,
        product_types: Optional[Iterable[Any]] = None,
        charge_type: Any = None,
        currencies: Optional[Iterable[str]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        trace_id: str = "",
        description: str = "",
        filter_text: str = "",
        amount: float = 0.0,
        skip: int = 0,
        limit: int = 0,
        sort: str = "",
    ) -> Page[Transaction]:
        """One page of the balance ledger."""
        return self._send(AccountTransactionsRequest(
            as_list(transaction_types), as_list(product_types), charge_type, as_list(currencies), since, until,
            trace_id, description, filter_text, amount, skip, limit, sort))

    def all_transactions(
        self,
        *,
        transaction_types: Optional[Iterable[Any]] = None,
        product_types: Optional[Iterable[Any]] = None,
        charge_type: Any = None,
        currencies: Optional[Iterable[str]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        trace_id: str = "",
        description: str = "",
        filter_text: str = "",
        amount: float = 0.0,
        sort: str = "",
        page_size: int = 100,
    ) -> Iterator[Transaction]:
        """Every matching transaction; pages are fetched as you iterate::

            for tx in client.account.all_transactions(since=month_start):
                print(tx.creation_time, tx.type, tx.change)
        """
        def fetch(skip: int, limit: int) -> Page[Transaction]:
            return self.transactions(
                transaction_types=transaction_types, product_types=product_types, charge_type=charge_type,
                currencies=currencies, since=since, until=until, trace_id=trace_id, description=description,
                filter_text=filter_text, amount=amount, skip=skip, limit=limit, sort=sort)

        return paginate(fetch, 0, page_size)

