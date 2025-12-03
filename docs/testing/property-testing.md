# Property-Based Testing

## Overview

Property-based testing com Hypothesis verifica invariantes usando dados gerados aleatoriamente.

## Configuration

```python
# tests/conftest.py
from hypothesis import settings, Verbosity

settings.register_profile("ci", max_examples=100)
settings.register_profile("dev", max_examples=10)
settings.load_profile("dev")
```

## Basic Properties

```python
from hypothesis import given, strategies as st

@given(st.emails())
def test_email_validation(email: str):
    """Any valid email should be accepted."""
    result = Email(email)
    assert "@" in result.value

@given(st.text(min_size=1, max_size=100))
def test_name_normalization_idempotent(name: str):
    """Normalization should be idempotent."""
    normalized = normalize_name(name)
    assert normalize_name(normalized) == normalized
```

## Custom Strategies

```python
from hypothesis import strategies as st

@st.composite
def users(draw):
    """Generate random valid users."""
    return User(
        id=draw(st.text(min_size=10, max_size=26, alphabet="0123456789ABCDEFGHJKMNPQRSTVWXYZ")),
        email=draw(st.emails()),
        name=draw(st.text(min_size=2, max_size=100)),
        is_active=draw(st.booleans()),
    )

@st.composite
def orders(draw):
    """Generate random valid orders."""
    items = draw(st.lists(order_items(), min_size=1, max_size=10))
    return Order(
        id=draw(st.uuids().map(str)),
        items=items,
        total=sum(item.subtotal for item in items),
    )
```

## Domain Invariants

```python
class TestOrderInvariants:
    @given(orders())
    def test_order_total_equals_sum_of_items(self, order):
        """Order total must equal sum of item subtotals."""
        expected = sum(item.subtotal for item in order.items)
        assert order.total == expected
    
    @given(orders())
    def test_order_has_at_least_one_item(self, order):
        """Order must have at least one item."""
        assert len(order.items) >= 1
```

## Specification Properties

```python
class TestSpecificationProperties:
    @given(st.integers(), st.integers())
    def test_and_is_commutative(self, a, b):
        """AND composition should be commutative."""
        spec1 = equals("value", a)
        spec2 = equals("value", b)
        obj = {"value": a}
        
        result1 = spec1.and_spec(spec2).is_satisfied_by(obj)
        result2 = spec2.and_spec(spec1).is_satisfied_by(obj)
        
        assert result1 == result2
    
    @given(st.integers())
    def test_double_negation_is_identity(self, value):
        """Double negation should be identity."""
        spec = equals("value", value)
        obj = {"value": value}
        
        original = spec.is_satisfied_by(obj)
        double_neg = spec.not_spec().not_spec().is_satisfied_by(obj)
        
        assert original == double_neg
```

## Round-Trip Properties

```python
@given(users())
def test_user_serialization_roundtrip(user):
    """Serializing and deserializing should preserve data."""
    serialized = user.model_dump_json()
    deserialized = User.model_validate_json(serialized)
    assert deserialized == user

@given(st.text())
def test_json_roundtrip(text):
    """JSON encode/decode should be identity."""
    encoded = json.dumps(text)
    decoded = json.loads(encoded)
    assert decoded == text
```

## Running Property Tests

```bash
# Run with default profile
pytest tests/properties/

# Run with CI profile (more examples)
pytest tests/properties/ --hypothesis-profile=ci

# Show examples
pytest tests/properties/ -v --hypothesis-show-statistics
```

## Best Practices

1. **Test invariants** - Properties that always hold
2. **Use custom strategies** - For domain objects
3. **Test round-trips** - Serialize/deserialize
4. **Keep properties simple** - One property per test
5. **Use profiles** - Different settings for dev/CI
