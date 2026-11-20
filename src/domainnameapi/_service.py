"""The base class of the services (``client.domains``, ``client.dns``, ...)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from .errors import OperationError
from .request import BaseRequest

if TYPE_CHECKING:  # pragma: no cover
    from .client import ApiResponse, Client


class Service:
    """A group of operations, named like a ``dna`` CLI command group."""

    __slots__ = ("_client",)

    def __init__(self, client: "Client"):
        self._client = client

    def __repr__(self) -> str:
        return "<%s>" % type(self).__name__

    def _send(self, request: BaseRequest) -> Any:
        return self._client.send(request)

    def _exchange(self, request: BaseRequest) -> "ApiResponse":
        return self._client.send_with_response(request)

    @staticmethod
    def _failed(request: BaseRequest, response: Optional["ApiResponse"], code: str, message: str) -> OperationError:
        ep = request.endpoint()
        return OperationError(ep.method, ep.path, code, message, response.correlation_id if response else "")


def first_text(*values: Optional[str]) -> str:
    for v in values:
        if v and v.strip():
            return v.strip()
    return ""
