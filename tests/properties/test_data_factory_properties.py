"""Property-based tests for Data Factory module.

**Feature: api-architecture-analysis, Property 15.5: Test Data Factory**
**Validates: Requirements 8.1, 8.2**
"""

import pytest
from hypothesis import given, strategies as st, settings
from dataclasses import dataclass
from datetime import datetime, date
from uuid import UUID

from src.my_api.shared.data_factory import (
    FieldType,
    FieldConfig,
    DataGenerator,
    FactoryConfig,
    DataFactory,
    FactoryRegistry,
    create_factory_config,
    quick_factory,
)


# Sample models for testing
@dataclass
class SampleUser:
    name: str
    email: str
    age: int


@dataclass
class SampleProduct:
    id: str
    name: str
    price: float
    active: bool


# Strategies
field_types = st.sampled_from(list(FieldType))
seeds = st.integers(min_value=0, max_value=10000)
counts = st.integers(min_value=1, max_value=20)
min_lengths = st.integers(min_value=1, max_value=10)
max_lengths = st.integers(min_value=11, max_value=50)


class TestDataGenerator:
    """Property tests for DataGenerator."""

    @given(seed=seeds)
    @settings(max_examples=100)
    def test_deterministic_with_seed(self, seed: int) -> None:
        """Same seed produces same values."""
        gen1 = DataGenerator(seed)
        gen2 = DataGenerator(seed)
        assert gen1.string(5, 10) == gen2.string(5, 10)
        assert gen1.integer(0, 100) == gen2.integer(0, 100)

    @given(min_len=min_lengths, max_len=max_lengths)
    @settings(max_examples=100)
    def test_string_length_bounds(self, min_len: int, max_len: int) -> None:
        """String length is within bounds."""
        gen = DataGenerator()
        result = gen.string(min_len, max_len)
        assert min_len <= len(result) <= max_len

    @given(min_val=st.integers(0, 100), max_val=st.integers(101, 1000))
    @settings(max_examples=100)
    def test_integer_bounds(self, min_val: int, max_val: int) -> None:
        """Integer is within bounds."""
        gen = DataGenerator()
        result = gen.integer(min_val, max_val)
        assert min_val <= result <= max_val

    @given(min_val=st.floats(0.0, 100.0), max_val=st.floats(101.0, 1000.0))
    @settings(max_examples=100)
    def test_float_bounds(self, min_val: float, max_val: float) -> None:
        """Float is within bounds."""
        gen = DataGenerator()
        result = gen.floating(min_val, max_val)
        assert min_val <= result <= max_val

    @given(seed=seeds)
    @settings(max_examples=100)
    def test_boolean_returns_bool(self, seed: int) -> None:
        """Boolean returns actual boolean."""
        gen = DataGenerator(seed)
        result = gen.boolean()
        assert isinstance(result, bool)

    @given(seed=seeds)
    @settings(max_examples=100)
    def test_uuid_returns_uuid(self, seed: int) -> None:
        """UUID returns actual UUID."""
        gen = DataGenerator(seed)
        result = gen.uuid()
        assert isinstance(result, UUID)

    @given(seed=seeds)
    @settings(max_examples=100)
    def test_datetime_returns_datetime(self, seed: int) -> None:
        """Datetime returns actual datetime."""
        gen = DataGenerator(seed)
        result = gen.datetime_value()
        assert isinstance(result, datetime)

    @given(seed=seeds)
    @settings(max_examples=100)
    def test_date_returns_date(self, seed: int) -> None:
        """Date returns actual date."""
        gen = DataGenerator(seed)
        result = gen.date_value()
        assert isinstance(result, date)

    @given(seed=seeds)
    @settings(max_examples=100)
    def test_email_format(self, seed: int) -> None:
        """Email has correct format."""
        gen = DataGenerator(seed)
        result = gen.email()
        assert "@" in result
        assert "." in result.split("@")[1]

    @given(seed=seeds)
    @settings(max_examples=100)
    def test_url_format(self, seed: int) -> None:
        """URL has correct format."""
        gen = DataGenerator(seed)
        result = gen.url()
        assert result.startswith("https://")

    @given(seed=seeds)
    @settings(max_examples=100)
    def test_phone_format(self, seed: int) -> None:
        """Phone has correct format."""
        gen = DataGenerator(seed)
        result = gen.phone()
        assert result.startswith("+1-")

    @given(options=st.lists(st.integers(), min_size=1, max_size=10))
    @settings(max_examples=100)
    def test_choice_from_options(self, options: list[int]) -> None:
        """Choice returns value from options."""
        gen = DataGenerator()
        result = gen.choice(options)
        assert result in options


class TestFieldConfig:
    """Property tests for FieldConfig."""

    @given(field_type=field_types, nullable=st.booleans())
    @settings(max_examples=100)
    def test_config_creation(self, field_type: FieldType, nullable: bool) -> None:
        """Config can be created with any field type."""
        config = FieldConfig(field_type=field_type, nullable=nullable)
        assert config.field_type == field_type
        assert config.nullable == nullable


class TestFactoryConfig:
    """Property tests for FactoryConfig."""

    @given(field_name=st.text(min_size=1, max_size=20), field_type=field_types)
    @settings(max_examples=100)
    def test_add_field(self, field_name: str, field_type: FieldType) -> None:
        """Fields can be added to config."""
        config = FactoryConfig()
        config.add_field(field_name, field_type)
        assert field_name in config.fields
        assert config.fields[field_name].field_type == field_type

    @given(field_names=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5, unique=True))
    @settings(max_examples=100)
    def test_multiple_fields(self, field_names: list[str]) -> None:
        """Multiple fields can be added."""
        config = FactoryConfig()
        for name in field_names:
            config.add_field(name, FieldType.STRING)
        assert len(config.fields) == len(field_names)


class TestDataFactory:
    """Property tests for DataFactory."""

    @given(seed=seeds)
    @settings(max_examples=50)
    def test_build_creates_instance(self, seed: int) -> None:
        """Build creates model instance."""
        config = FactoryConfig()
        config.add_field("name", FieldType.NAME)
        config.add_field("email", FieldType.EMAIL)
        config.add_field("age", FieldType.INTEGER, min_value=18, max_value=100)
        factory = DataFactory(SampleUser, config, seed)
        user = factory.build()
        assert isinstance(user, SampleUser)
        assert isinstance(user.name, str)
        assert "@" in user.email
        assert 18 <= user.age <= 100

    @given(count=counts)
    @settings(max_examples=50)
    def test_build_batch_count(self, count: int) -> None:
        """Build batch creates correct count."""
        config = FactoryConfig()
        config.add_field("name", FieldType.NAME)
        config.add_field("email", FieldType.EMAIL)
        config.add_field("age", FieldType.INTEGER)
        factory = DataFactory(SampleUser, config)
        users = factory.build_batch(count)
        assert len(users) == count

    @given(name=st.text(min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_override_field(self, name: str) -> None:
        """Override replaces generated value."""
        config = FactoryConfig()
        config.add_field("name", FieldType.NAME)
        config.add_field("email", FieldType.EMAIL)
        config.add_field("age", FieldType.INTEGER)
        factory = DataFactory(SampleUser, config)
        user = factory.build(name=name)
        assert user.name == name

    @given(seed=seeds)
    @settings(max_examples=50)
    def test_build_dict(self, seed: int) -> None:
        """Build dict returns dictionary."""
        config = FactoryConfig()
        config.add_field("name", FieldType.NAME)
        config.add_field("email", FieldType.EMAIL)
        config.add_field("age", FieldType.INTEGER)
        factory = DataFactory(SampleUser, config, seed)
        data = factory.build_dict()
        assert isinstance(data, dict)
        assert "name" in data
        assert "email" in data
        assert "age" in data

    @given(seed=seeds)
    @settings(max_examples=50)
    def test_sequence_increments(self, seed: int) -> None:
        """Sequence increments on each call."""
        config = FactoryConfig()
        config.add_field("name", FieldType.NAME)
        config.add_field("email", FieldType.EMAIL)
        config.add_field("age", FieldType.INTEGER)
        factory = DataFactory(SampleUser, config, seed)
        seq1 = factory.sequence
        seq2 = factory.sequence
        seq3 = factory.sequence
        assert seq2 == seq1 + 1
        assert seq3 == seq2 + 1

    def test_reset_sequence(self) -> None:
        """Reset sequence resets to 0."""
        config = FactoryConfig()
        config.add_field("name", FieldType.NAME)
        config.add_field("email", FieldType.EMAIL)
        config.add_field("age", FieldType.INTEGER)
        factory = DataFactory(SampleUser, config)
        _ = factory.sequence
        _ = factory.sequence
        factory.reset_sequence()
        assert factory.sequence == 1


class TestFactoryRegistry:
    """Property tests for FactoryRegistry."""

    @given(factory_name=st.text(min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_register_and_get(self, factory_name: str) -> None:
        """Registered factory can be retrieved."""
        registry = FactoryRegistry()
        config = FactoryConfig()
        config.add_field("name", FieldType.NAME)
        config.add_field("email", FieldType.EMAIL)
        config.add_field("age", FieldType.INTEGER)
        factory = DataFactory(SampleUser, config)
        registry.register(factory_name, factory)
        retrieved = registry.get(factory_name)
        assert retrieved is not None

    @given(factory_name=st.text(min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_create_from_registry(self, factory_name: str) -> None:
        """Create from registry produces instance."""
        registry = FactoryRegistry()
        config = FactoryConfig()
        config.add_field("name", FieldType.NAME)
        config.add_field("email", FieldType.EMAIL)
        config.add_field("age", FieldType.INTEGER)
        factory = DataFactory(SampleUser, config)
        registry.register(factory_name, factory)
        user = registry.create(factory_name)
        assert isinstance(user, SampleUser)

    @given(factory_names=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5, unique=True))
    @settings(max_examples=50)
    def test_list_factories(self, factory_names: list[str]) -> None:
        """List factories returns all names."""
        registry = FactoryRegistry()
        config = FactoryConfig()
        config.add_field("name", FieldType.NAME)
        config.add_field("email", FieldType.EMAIL)
        config.add_field("age", FieldType.INTEGER)
        for name in factory_names:
            registry.register(name, DataFactory(SampleUser, config))
        listed = registry.list_factories()
        assert set(listed) == set(factory_names)


class TestQuickFactory:
    """Property tests for quick_factory helper."""

    def test_quick_factory_creates_factory(self) -> None:
        """Quick factory creates working factory."""
        factory = quick_factory(
            SampleProduct,
            id=FieldType.UUID,
            name=FieldType.NAME,
            price=FieldType.FLOAT,
            active=FieldType.BOOLEAN,
        )
        product = factory.build()
        assert isinstance(product, SampleProduct)
