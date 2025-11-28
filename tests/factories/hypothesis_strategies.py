"""Generic Hypothesis strategies for property-based testing.

**Feature: api-architecture-analysis, Task 4.2: Generic Hypothesis Strategies**
**Validates: Requirements 8.2**

Usage:
    from tests.factories.hypothesis_strategies import (
        entity_strategy, pydantic_strategy, ulid_strategy, email_strategy,
    )
"""

from datetime import datetime, timezone
from typing import Any, TypeVar, get_args, get_origin

from hypothesis import strategies as st
from pydantic import BaseModel
from pydantic.fields import FieldInfo

T = TypeVar("T", bound=BaseModel)

# =============================================================================
# ID Strategies
# =============================================================================

CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ulid_strategy = st.text(alphabet=CROCKFORD_ALPHABET, min_size=26, max_size=26)
uuid_strategy = st.uuids().map(str)
entity_id_strategy = st.one_of(ulid_strategy, uuid_strategy)

# =============================================================================
# String Strategies
# =============================================================================

SAFE_ALPHABET = st.characters(whitelist_categories=("L", "N"))
non_empty_str_strategy = st.text(min_size=1, max_size=100, alphabet=SAFE_ALPHABET)
short_str_strategy = st.text(min_size=1, max_size=50, alphabet=SAFE_ALPHABET)
medium_str_strategy = st.text(min_size=1, max_size=255, alphabet=SAFE_ALPHABET)
long_str_strategy = st.text(min_size=1, max_size=1000, alphabet=SAFE_ALPHABET)
slug_strategy = st.from_regex(r"^[a-z0-9]+(-[a-z0-9]+)*$", fullmatch=True).filter(
    lambda s: 1 <= len(s) <= 100
)

# =============================================================================
# Contact Strategies
# =============================================================================

email_strategy = st.emails()
phone_strategy = st.from_regex(r"^\+?[0-9]{10,15}$", fullmatch=True)

# =============================================================================
# Numeric Strategies
# =============================================================================

positive_int_strategy = st.integers(min_value=1, max_value=1_000_000)
non_negative_int_strategy = st.integers(min_value=0, max_value=1_000_000)
positive_float_strategy = st.floats(
    min_value=0.01, max_value=1_000_000, allow_nan=False, allow_infinity=False
)
non_negative_float_strategy = st.floats(
    min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False
)
percentage_strategy = st.floats(
    min_value=0, max_value=100, allow_nan=False, allow_infinity=False
)
price_strategy = st.floats(
    min_value=0.01, max_value=100_000, allow_nan=False, allow_infinity=False
).map(lambda x: round(x, 2))

# =============================================================================
# Pagination Strategies
# =============================================================================

page_number_strategy = st.integers(min_value=1, max_value=1000)
page_size_strategy = st.integers(min_value=1, max_value=100)

# =============================================================================
# DateTime Strategies
# =============================================================================

datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 12, 31),
    timezones=st.just(timezone.utc),
)
past_datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime.now(),
    timezones=st.just(timezone.utc),
)
bool_strategy = st.booleans()


# =============================================================================
# Helper Functions
# =============================================================================


def _get_string_strategy(field_info: FieldInfo | None) -> st.SearchStrategy[str]:
    """Get string strategy based on field constraints."""
    min_length = 1
    max_length = 100
    if field_info:
        metadata = getattr(field_info, "metadata", [])
        for meta in metadata:
            if hasattr(meta, "min_length") and meta.min_length is not None:
                min_length = meta.min_length
            if hasattr(meta, "max_length") and meta.max_length is not None:
                max_length = meta.max_length
    return st.text(min_size=min_length, max_size=max_length, alphabet=SAFE_ALPHABET)


def _get_int_strategy(field_info: FieldInfo | None) -> st.SearchStrategy[int]:
    """Get integer strategy based on field constraints."""
    min_value = 0
    max_value = 1_000_000
    if field_info:
        metadata = getattr(field_info, "metadata", [])
        for meta in metadata:
            if hasattr(meta, "gt") and meta.gt is not None:
                min_value = meta.gt + 1
            if hasattr(meta, "ge") and meta.ge is not None:
                min_value = meta.ge
            if hasattr(meta, "lt") and meta.lt is not None:
                max_value = meta.lt - 1
            if hasattr(meta, "le") and meta.le is not None:
                max_value = meta.le
    return st.integers(min_value=min_value, max_value=max_value)


def _get_float_strategy(field_info: FieldInfo | None) -> st.SearchStrategy[float]:
    """Get float strategy based on field constraints."""
    min_value = 0.0
    max_value = 1_000_000.0
    exclude_min = False
    if field_info:
        metadata = getattr(field_info, "metadata", [])
        for meta in metadata:
            if hasattr(meta, "gt") and meta.gt is not None:
                min_value = meta.gt
                exclude_min = True
            if hasattr(meta, "ge") and meta.ge is not None:
                min_value = meta.ge
            if hasattr(meta, "lt") and meta.lt is not None:
                max_value = meta.lt - 0.01
            if hasattr(meta, "le") and meta.le is not None:
                max_value = meta.le
    if exclude_min:
        min_value += 0.01
    return st.floats(
        min_value=min_value, max_value=max_value, allow_nan=False, allow_infinity=False
    )


def _get_strategy_for_type(
    field_type: type, field_info: FieldInfo | None = None
) -> st.SearchStrategy[Any]:
    """Get a Hypothesis strategy for a given Python type."""
    origin = get_origin(field_type)
    args = get_args(field_type)

    if field_type is type(None):
        return st.none()

    # Handle Union types (including Optional)
    if origin is type(int | str):
        non_none = [a for a in args if a is not type(None)]
        if not non_none:
            return st.none()
        strategies = [_get_strategy_for_type(a, field_info) for a in non_none]
        if type(None) in args:
            strategies.append(st.none())
        return st.one_of(*strategies)

    if origin is list:
        elem = args[0] if args else str
        return st.lists(_get_strategy_for_type(elem, None), min_size=0, max_size=10)

    if origin is dict:
        k = args[0] if args else str
        v = args[1] if len(args) > 1 else str
        return st.dictionaries(
            _get_strategy_for_type(k, None),
            _get_strategy_for_type(v, None),
            min_size=0,
            max_size=5,
        )

    if field_type is str:
        return _get_string_strategy(field_info)
    if field_type is int:
        return _get_int_strategy(field_info)
    if field_type is float:
        return _get_float_strategy(field_info)
    if field_type is bool:
        return bool_strategy
    if field_type is datetime:
        return datetime_strategy

    if isinstance(field_type, type) and issubclass(field_type, BaseModel):
        return pydantic_strategy(field_type)

    return st.none()


# =============================================================================
# Generic Model Strategies
# =============================================================================


def pydantic_strategy(model_class: type[T]) -> st.SearchStrategy[T]:
    """Create a Hypothesis strategy for a Pydantic model."""
    field_strategies: dict[str, st.SearchStrategy[Any]] = {}
    for field_name, field_info in model_class.model_fields.items():
        field_type = field_info.annotation
        if field_type is None:
            field_strategies[field_name] = st.none()
        else:
            field_strategies[field_name] = _get_strategy_for_type(field_type, field_info)
    return st.builds(model_class, **field_strategies)


def entity_strategy(
    entity_class: type[T], *, with_id: bool = True, with_timestamps: bool = True
) -> st.SearchStrategy[T]:
    """Create a Hypothesis strategy for a domain entity."""
    field_strategies: dict[str, st.SearchStrategy[Any]] = {}
    for field_name, field_info in entity_class.model_fields.items():
        field_type = field_info.annotation
        if field_name == "id":
            field_strategies[field_name] = ulid_strategy if with_id else st.none()
            continue
        if field_name in ("created_at", "updated_at"):
            if with_timestamps:
                field_strategies[field_name] = datetime_strategy
            else:
                field_strategies[field_name] = st.just(datetime.now(tz=timezone.utc))
            continue
        if field_name == "is_deleted":
            field_strategies[field_name] = st.just(False)
            continue
        if field_type is None:
            field_strategies[field_name] = st.none()
        else:
            field_strategies[field_name] = _get_strategy_for_type(field_type, field_info)
    return st.builds(entity_class, **field_strategies)


def create_dto_strategy(dto_class: type[T]) -> st.SearchStrategy[T]:
    """Create a Hypothesis strategy for a Create DTO."""
    return pydantic_strategy(dto_class)


def update_dto_strategy(dto_class: type[T]) -> st.SearchStrategy[T]:
    """Create a Hypothesis strategy for an Update DTO."""
    field_strategies: dict[str, st.SearchStrategy[Any]] = {}
    for field_name, field_info in dto_class.model_fields.items():
        field_type = field_info.annotation
        if field_type is None:
            field_strategies[field_name] = st.none()
            continue
        base = _get_strategy_for_type(field_type, field_info)
        origin = get_origin(field_type)
        args = get_args(field_type)
        is_optional = origin is type(int | str) and type(None) in args
        if is_optional:
            field_strategies[field_name] = st.one_of(st.none(), base)
        else:
            field_strategies[field_name] = base
    return st.builds(dto_class, **field_strategies)


# =============================================================================
# Composite Strategies
# =============================================================================


def list_of(
    strategy: st.SearchStrategy[T], *, min_size: int = 0, max_size: int = 10
) -> st.SearchStrategy[list[T]]:
    """Create a strategy for lists of items."""
    return st.lists(strategy, min_size=min_size, max_size=max_size)


def optional(strategy: st.SearchStrategy[T]) -> st.SearchStrategy[T | None]:
    """Create a strategy that may return None."""
    return st.one_of(st.none(), strategy)


def one_of_models(*model_classes: type[T]) -> st.SearchStrategy[T]:
    """Create a strategy that generates one of several model types."""
    strategies = [pydantic_strategy(cls) for cls in model_classes]
    return st.one_of(*strategies)


def strategy_for_field(field_name: str, field_type: type) -> st.SearchStrategy[Any]:
    """Create a strategy for a specific field with heuristics based on name."""
    name_lower = field_name.lower()
    if "email" in name_lower:
        return email_strategy
    if "phone" in name_lower:
        return phone_strategy
    if "price" in name_lower or "cost" in name_lower or "amount" in name_lower:
        return price_strategy
    if "percentage" in name_lower or "percent" in name_lower:
        return percentage_strategy
    if "slug" in name_lower:
        return slug_strategy
    if "id" in name_lower and field_type is str:
        return ulid_strategy
    return _get_strategy_for_type(field_type, None)


def create_model_strategy(
    model_class: type[T], overrides: dict[str, st.SearchStrategy[Any]] | None = None
) -> st.SearchStrategy[T]:
    """Create a model strategy with field overrides."""
    field_strategies: dict[str, st.SearchStrategy[Any]] = {}
    for field_name, field_info in model_class.model_fields.items():
        if overrides and field_name in overrides:
            field_strategies[field_name] = overrides[field_name]
        else:
            field_type = field_info.annotation
            if field_type is None:
                field_strategies[field_name] = st.none()
            else:
                field_strategies[field_name] = _get_strategy_for_type(field_type, field_info)
    return st.builds(model_class, **field_strategies)
