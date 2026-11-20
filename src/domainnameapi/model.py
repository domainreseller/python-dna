"""Response models and the helpers that declare them.

Every model is a :mod:`dataclasses` dataclass that subclasses :class:`Model`.
Each field says which JSON property it reads and how to convert it::

    from dataclasses import dataclass
    from datetime import datetime
    from typing import Optional

    from domainnameapi.model import Model, integer, text, timestamp

    @dataclass
    class Expiry(Model):
        domain_name: str = text("domainName")
        expiration_date: Optional[datetime] = timestamp("expirationDate")
        remaining_days: int = integer("remainingDay")

    expiry = Expiry.from_api({"domainName": "example.com", "remainingDay": 30})

Decoding is forgiving, because the API is: a missing or ``null`` property
gives the field's default, dates without a time zone are read as UTC,
``"0001-01-01T00:00:00"`` and unparseable dates become ``None``, numbers sent
as strings are converted, ``[]`` sent instead of ``{}`` is accepted, and
property names match in any case. The decoded JSON object stays available as
``model.raw``, for properties this package does not model yet.
"""

from __future__ import annotations

import dataclasses
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, Type, TypeVar, Union

__all__ = [
    "Converter",
    "Model",
    "Page",
    "attributes",
    "boolean",
    "enum_list",
    "enum_value",
    "integer",
    "integers",
    "list_of",
    "model",
    "model_list",
    "number",
    "optional_boolean",
    "optional_integer",
    "optional_model",
    "page_of",
    "parse_time",
    "raw",
    "text",
    "texts",
    "timestamp",
]

M = TypeVar("M", bound="Model")
T = TypeVar("T")


# ---------------------------------------------------------------------------
# Converters


class Converter:
    """Turns one decoded JSON value into a Python value.

    ``nested`` is the model class a converter produces (directly or as list
    items), so tools can walk the model tree; ``many`` tells whether it
    produces a list.
    """

    nested: Optional[type] = None
    many: bool = False

    def default(self) -> Any:
        return None

    def decode(self, value: Any) -> Any:
        return value

    def __call__(self, value: Any) -> Any:
        return self.default() if value is None else self.decode(value)


class _Text(Converter):
    def default(self) -> str:
        return ""

    def decode(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return _number_text(value)
        if isinstance(value, (dict, list)):
            return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        return str(value)


class _Integer(Converter):
    def default(self) -> int:
        return 0

    def decode(self, value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value.strip()))
            except ValueError:
                return 0
        return 0


class _OptionalInteger(_Integer):
    def default(self) -> Optional[int]:  # type: ignore[override]
        return None


class _Number(Converter):
    def default(self) -> float:
        return 0.0

    def decode(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                return 0.0
        return 0.0


class _Boolean(Converter):
    def default(self) -> bool:
        return False

    def decode(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "yes", "on")
        return False


class _OptionalBoolean(_Boolean):
    def default(self) -> Optional[bool]:  # type: ignore[override]
        return None


class _Timestamp(Converter):
    def decode(self, value: Any) -> Optional[datetime]:
        return parse_time(value) if isinstance(value, str) else None


class _Attributes(Converter):
    def default(self) -> Dict[str, str]:
        return {}

    def decode(self, value: Any) -> Dict[str, str]:
        if not isinstance(value, dict):
            return {}  # null, [] or something unexpected
        return {str(k): _TEXT.decode(v) if v is not None else "" for k, v in value.items()}


class _Raw(Converter):
    pass


class _Enum(Converter):
    def __init__(self, enum_cls: Any):
        self.enum_cls = enum_cls

    def decode(self, value: Any) -> Any:
        from_api = getattr(self.enum_cls, "from_api", None)
        if from_api is not None:
            return from_api(value)
        try:
            return self.enum_cls(value)
        except ValueError:
            return value


class _Nested(Converter):
    def __init__(self, model_cls: Type[Model], optional: bool = False):
        self.nested = model_cls
        self.optional = optional

    def default(self) -> Any:
        return None if self.optional else self.nested()  # type: ignore[misc]

    def decode(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return self.default()
        return self.nested.from_api(value)  # type: ignore[union-attr]


class _List(Converter):
    many = True

    def __init__(self, item: Converter):
        self.item = item
        self.nested = item.nested

    def default(self) -> list:
        return []

    def decode(self, value: Any) -> list:
        if not isinstance(value, list):
            return []
        return [self.item(v) for v in value]


class _Page(Converter):
    many = True

    def __init__(self, item: Converter):
        self.item = item
        self.nested = item.nested

    def default(self) -> Page:
        return Page([], 0)

    def decode(self, value: Any) -> Page:
        if not isinstance(value, dict):
            return Page([], 0)
        items = _lookup(value, "items")
        return Page(_List(self.item)(items), _INTEGER(_lookup(value, "totalCount")))


_TEXT = _Text()
_INTEGER = _Integer()
_NUMBER = _Number()
_BOOLEAN = _Boolean()
_TIMESTAMP = _Timestamp()


def _number_text(value: Union[int, float]) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def list_of(item: Union[Converter, Type[Model]]) -> Converter:
    """A converter for a JSON array whose items are models or converted values."""
    return _List(_as_converter(item))


def page_of(item: Union[Converter, Type[Model]]) -> Converter:
    """A converter for ``{"items": [...], "totalCount": n}``, producing a :class:`Page`."""
    return _Page(_as_converter(item))


def _as_converter(spec: Any) -> Converter:
    if isinstance(spec, Converter):
        return spec
    if isinstance(spec, type) and issubclass(spec, Model):
        return _Nested(spec)
    raise TypeError("expected a Model subclass or a Converter, got %r" % (spec,))


def decode_as(spec: Any, data: Any) -> Any:
    """Decode ``data`` with a request's ``response`` spec (``None`` keeps the JSON)."""
    if spec is None:
        return data
    if data is None and not (isinstance(spec, Converter) and spec.many):
        return None
    return _as_converter(spec)(data)


# ---------------------------------------------------------------------------
# Field declarations


def _field(api: str, conv: Converter) -> Any:
    default = conv.default()
    metadata = {"api": api, "conv": conv}
    if isinstance(default, (list, dict, Model, Page)):
        return dataclasses.field(default_factory=conv.default, metadata=metadata)
    return dataclasses.field(default=default, metadata=metadata)


def text(api: str) -> Any:
    """A string property (``""`` when missing)."""
    return _field(api, _TEXT)


def integer(api: str) -> Any:
    """An integer property (``0`` when missing)."""
    return _field(api, _INTEGER)


def optional_integer(api: str) -> Any:
    """An integer property that may be absent (``None`` when missing)."""
    return _field(api, _OptionalInteger())


def number(api: str) -> Any:
    """A decimal property such as a price (``0.0`` when missing)."""
    return _field(api, _NUMBER)


def boolean(api: str) -> Any:
    """A boolean property (``False`` when missing)."""
    return _field(api, _BOOLEAN)


def optional_boolean(api: str) -> Any:
    """A boolean property that may be absent (``None`` when missing)."""
    return _field(api, _OptionalBoolean())


def timestamp(api: str) -> Any:
    """A date and time, as an aware UTC :class:`~datetime.datetime` (``None`` when missing)."""
    return _field(api, _TIMESTAMP)


def attributes(api: str) -> Any:
    """A string-to-string object such as registry attributes (``{}`` when missing)."""
    return _field(api, _Attributes())


def raw(api: str) -> Any:
    """A property kept exactly as decoded from JSON (``None`` when missing)."""
    return _field(api, _Raw())


def enum_value(api: str, enum_cls: Any) -> Any:
    """A named value (``None`` when missing; unknown values never fail)."""
    return _field(api, _Enum(enum_cls))


def texts(api: str) -> Any:
    """A list of strings."""
    return _field(api, _List(_TEXT))


def integers(api: str) -> Any:
    """A list of integers."""
    return _field(api, _List(_INTEGER))


def enum_list(api: str, enum_cls: Any) -> Any:
    """A list of named values."""
    return _field(api, _List(_Enum(enum_cls)))


def model(api: str, model_cls: Type[Model]) -> Any:
    """A nested object (an empty model when missing)."""
    return _field(api, _Nested(model_cls))


def optional_model(api: str, model_cls: Type[Model]) -> Any:
    """A nested object that may be absent (``None`` when missing)."""
    return _field(api, _Nested(model_cls, optional=True))


def model_list(api: str, model_cls: Type[Model]) -> Any:
    """A list of nested objects."""
    return _field(api, _List(_Nested(model_cls)))


# ---------------------------------------------------------------------------
# Model


def _lookup(data: dict, key: str) -> Any:
    if key in data:
        return data[key]
    lower = key.lower()
    for k, v in data.items():
        if isinstance(k, str) and k.lower() == lower:
            return v
    return None


class Model:
    """Base class of the response models (and of models you declare yourself)."""

    @classmethod
    def from_api(cls: Type[M], data: Any) -> M:
        """Build the model from a decoded JSON object; anything else gives an empty model."""
        if not isinstance(data, dict):
            data = {}
        values = {}
        for f in dataclasses.fields(cls):  # type: ignore[arg-type]
            api = f.metadata.get("api")
            if api is None:
                continue
            values[f.name] = f.metadata["conv"](_lookup(data, api))
        obj = cls(**values)
        object.__setattr__(obj, "_raw", data)
        return obj

    @property
    def raw(self) -> Dict[str, Any]:
        """The JSON object this model was decoded from (``{}`` for models you built)."""
        return getattr(self, "_raw", {})

    @classmethod
    def api_fields(cls) -> Dict[str, Converter]:
        """The JSON property name and converter of every field, in declaration order."""
        return {f.metadata["api"]: f.metadata["conv"]
                for f in dataclasses.fields(cls) if "api" in f.metadata}  # type: ignore[arg-type]


@dataclasses.dataclass
class Page(Generic[T]):
    """One page of a list endpoint. Iterate it like a list."""

    #: The items of this page.
    items: List[T]
    #: The number of items across all pages.
    total_count: int = 0

    def __iter__(self) -> Iterator[T]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> T:
        return self.items[index]


def paginate(fetch: Callable[[int, int], Page[T]], skip: int = 0, page_size: int = 100) -> Iterator[T]:
    """Yield every item, calling ``fetch(skip, limit)`` for each page."""
    if page_size <= 0:
        page_size = 100
    while True:
        page = fetch(skip, page_size)
        for item in page.items:
            yield item
        nxt = skip + len(page.items)
        if not page.items:
            return
        if page.total_count > 0 and nxt >= page.total_count:
            return
        if page.total_count <= 0 and len(page.items) < page_size:
            return
        skip = nxt


# ---------------------------------------------------------------------------
# Time

_TIME_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})"
    r"(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?)?"
    r"\s*(Z|[+-]\d{2}:?\d{2})?$",
    re.IGNORECASE,
)


def parse_time(value: Any) -> Optional[datetime]:
    """Parse an API timestamp into an aware UTC datetime, or ``None``.

    Accepts ISO 8601 with or without a time zone ("2024-03-15T10:20:30",
    "2024-03-15T10:20:30.1234567Z", "2024-03-15 10:20:30+03:00", "2024-03-15").
    Times without a zone are UTC. ``"0001-01-01T00:00:00"`` and anything
    unparseable give ``None``.
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str):
        return None
    m = _TIME_RE.match(value.strip())
    if not m:
        return None
    year, month, day, hour, minute, second, frac, zone = m.groups()
    try:
        micro = int((frac or "0")[:6].ljust(6, "0"))
        dt = datetime(int(year), int(month), int(day), int(hour or 0), int(minute or 0), int(second or 0), micro,
                      tzinfo=timezone.utc)
        if zone and zone.upper() != "Z":
            sign = 1 if zone[0] == "+" else -1
            digits = zone[1:].replace(":", "")
            offset = sign * (int(digits[:2]) * 60 + int(digits[2:]))
            dt = dt - timedelta(minutes=offset)
    except (ValueError, OverflowError):
        return None
    if dt.year <= 1:
        return None
    return dt
