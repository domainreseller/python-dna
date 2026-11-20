"""Orders. CLI: ``dna order ...``"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ._service import Service
from .enums import OrderProductStatus, OrderStatus, OrderType, ProductType
from .model import Model, enum_value, integer, model_list, number, text
from .request import BaseRequest, Safety, Validator

__all__ = ["Order", "OrderGetRequest", "OrderProduct", "OrderService"]


@dataclass
class OrderProduct(Model):
    """One line of an order."""

    product_code: str = text("productCode")
    product_type: Optional[ProductType] = enum_value("productType", ProductType)
    order_type: Optional[OrderType] = enum_value("orderType", OrderType)
    status: Optional[OrderProductStatus] = enum_value("status", OrderProductStatus)
    price: float = number("price")
    price_currency: str = text("priceCurrency")
    name: str = text("name")
    description: str = text("description")
    additional_data: str = text("additionalData")
    period: int = integer("period")


@dataclass
class Order(Model):
    """An order and its lines."""

    order_code: str = text("orderCode")
    status: Optional[OrderStatus] = enum_value("status", OrderStatus)
    amount: float = number("amount")
    amount_currency: str = text("amountCurrency")
    products: List[OrderProduct] = model_list("products", OrderProduct)


@dataclass
class OrderGetRequest(BaseRequest):
    """Read an order. CLI: ``dna order get``"""

    method = "GET"
    path = "/api/v1/order/{order_code}"
    safety = Safety.READ
    response = Order

    order_code: str = ""

    def validate(self, v: Validator) -> None:
        v.required("order_code", self.order_code)


class OrderService(Service):
    """Orders and their lines. CLI: ``dna order``"""

    __slots__ = ()

    def get(self, order_code: str) -> Order:
        """An order and its lines."""
        return self._send(OrderGetRequest(order_code))
