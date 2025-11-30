"""Test Data Factory Module.

Provides generic data factory with Faker integration
for realistic test data generation.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Any
from collections.abc import Callable
from uuid import UUID, uuid4
import random
import string


class FieldType(Enum):
    """Types of fields for generation."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    UUID = "uuid"
    DATETIME = "datetime"
    DATE = "date"
    EMAIL = "email"
    NAME = "name"
    TEXT = "text"
    URL = "url"
    PHONE = "phone"
    ADDRESS = "address"
    COMPANY = "company"


@dataclass
class FieldConfig:
    """Configuration for a field."""
    field_type: FieldType
    nullable: bool = False
    min_value: int | float | None = None
    max_value: int | float | None = None
    min_length: int | None = None
    max_length: int | None = None
    choices: list[Any] | None = None
    pattern: str | None = None
    custom_generator: Callable[[], Any] | None = None


class DataGenerator:
    """Generates random data for various types."""
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
        self._surnames = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
        self._domains = ["example.com", "test.org", "demo.net", "sample.io"]
        self._companies = ["Acme Corp", "Tech Inc", "Global Ltd", "Digital Co", "Smart Systems"]
        self._streets = ["Main St", "Oak Ave", "Park Rd", "Lake Dr", "Hill Ln"]
        self._cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]

    def string(self, min_len: int = 5, max_len: int = 20) -> str:
        length = self._rng.randint(min_len, max_len)
        return "".join(self._rng.choices(string.ascii_letters, k=length))

    def integer(self, min_val: int = 0, max_val: int = 1000) -> int:
        return self._rng.randint(min_val, max_val)

    def floating(self, min_val: float = 0.0, max_val: float = 1000.0) -> float:
        return self._rng.uniform(min_val, max_val)

    def boolean(self) -> bool:
        return self._rng.choice([True, False])

    def uuid(self) -> UUID:
        return uuid4()

    def datetime_value(self, start_year: int = 2020, end_year: int = 2025) -> datetime:
        start = datetime(start_year, 1, 1)
        end = datetime(end_year, 12, 31)
        delta = end - start
        random_days = self._rng.randint(0, delta.days)
        return start + timedelta(days=random_days)

    def date_value(self, start_year: int = 2020, end_year: int = 2025) -> date:
        return self.datetime_value(start_year, end_year).date()

    def email(self) -> str:
        name = self._rng.choice(self._names).lower()
        domain = self._rng.choice(self._domains)
        num = self._rng.randint(1, 999)
        return f"{name}{num}@{domain}"

    def name(self) -> str:
        return f"{self._rng.choice(self._names)} {self._rng.choice(self._surnames)}"

    def first_name(self) -> str:
        return self._rng.choice(self._names)

    def last_name(self) -> str:
        return self._rng.choice(self._surnames)

    def text(self, sentences: int = 3) -> str:
        words = ["lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit"]
        result = []
        for _ in range(sentences):
            sentence_len = self._rng.randint(5, 15)
            sentence = " ".join(self._rng.choices(words, k=sentence_len))
            result.append(sentence.capitalize() + ".")
        return " ".join(result)

    def url(self) -> str:
        domain = self._rng.choice(self._domains)
        path = self.string(5, 10).lower()
        return f"https://{domain}/{path}"

    def phone(self) -> str:
        area = self._rng.randint(100, 999)
        prefix = self._rng.randint(100, 999)
        line = self._rng.randint(1000, 9999)
        return f"+1-{area}-{prefix}-{line}"

    def address(self) -> str:
        num = self._rng.randint(1, 9999)
        street = self._rng.choice(self._streets)
        city = self._rng.choice(self._cities)
        return f"{num} {street}, {city}"

    def company(self) -> str:
        return self._rng.choice(self._companies)

    def choice(self, options: list[Any]) -> Any:
        return self._rng.choice(options)

    def generate(self, config: FieldConfig) -> Any:
        if config.nullable and self._rng.random() < 0.1:
            return None
        if config.custom_generator:
            return config.custom_generator()
        if config.choices:
            return self.choice(config.choices)

        generators = {
            FieldType.STRING: lambda: self.string(config.min_length or 5, config.max_length or 20),
            FieldType.INTEGER: lambda: self.integer(int(config.min_value or 0), int(config.max_value or 1000)),
            FieldType.FLOAT: lambda: self.floating(float(config.min_value or 0), float(config.max_value or 1000)),
            FieldType.BOOLEAN: self.boolean,
            FieldType.UUID: self.uuid,
            FieldType.DATETIME: self.datetime_value,
            FieldType.DATE: self.date_value,
            FieldType.EMAIL: self.email,
            FieldType.NAME: self.name,
            FieldType.TEXT: self.text,
            FieldType.URL: self.url,
            FieldType.PHONE: self.phone,
            FieldType.ADDRESS: self.address,
            FieldType.COMPANY: self.company,
        }
        return generators.get(config.field_type, self.string)()


@dataclass
class FactoryConfig:
    """Configuration for a data factory."""
    fields: dict[str, FieldConfig] = field(default_factory=dict)
    post_generation: Callable[[dict[str, Any]], dict[str, Any]] | None = None

    def add_field(self, name: str, field_type: FieldType, **kwargs: Any) -> "FactoryConfig":
        self.fields[name] = FieldConfig(field_type=field_type, **kwargs)
        return self


class DataFactory[T]:
    """Generic data factory for creating test instances."""
    def __init__(self, model_class: type[T], config: FactoryConfig | None = None, seed: int | None = None) -> None:
        self._model_class = model_class
        self._config = config or FactoryConfig()
        self._generator = DataGenerator(seed)
        self._sequence = 0

    @property
    def sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def reset_sequence(self) -> None:
        self._sequence = 0

    def build(self, **overrides: Any) -> T:
        data: dict[str, Any] = {}
        for name, field_config in self._config.fields.items():
            if name in overrides:
                data[name] = overrides[name]
            else:
                data[name] = self._generator.generate(field_config)
        for key, value in overrides.items():
            if key not in data:
                data[key] = value
        if self._config.post_generation:
            data = self._config.post_generation(data)
        return self._model_class(**data)

    def build_batch(self, count: int, **overrides: Any) -> list[T]:
        return [self.build(**overrides) for _ in range(count)]

    def build_dict(self, **overrides: Any) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for name, field_config in self._config.fields.items():
            if name in overrides:
                data[name] = overrides[name]
            else:
                data[name] = self._generator.generate(field_config)
        for key, value in overrides.items():
            if key not in data:
                data[key] = value
        if self._config.post_generation:
            data = self._config.post_generation(data)
        return data


class FactoryRegistry:
    """Registry for data factories."""
    def __init__(self) -> None:
        self._factories: dict[str, DataFactory[Any]] = {}

    def register(self, name: str, factory: DataFactory[Any]) -> None:
        self._factories[name] = factory

    def get(self, name: str) -> DataFactory[Any] | None:
        return self._factories.get(name)

    def create(self, name: str, **overrides: Any) -> Any:
        factory = self.get(name)
        if factory is None:
            raise KeyError(f"Factory '{name}' not found")
        return factory.build(**overrides)

    def create_batch(self, name: str, count: int, **overrides: Any) -> list[Any]:
        factory = self.get(name)
        if factory is None:
            raise KeyError(f"Factory '{name}' not found")
        return factory.build_batch(count, **overrides)

    def list_factories(self) -> list[str]:
        return list(self._factories.keys())


def create_factory_config() -> FactoryConfig:
    """Create a new factory configuration."""
    return FactoryConfig()


def quick_factory[T](model_class: type[T], **field_types: FieldType) -> DataFactory[T]:
    """Create a quick factory with field types."""
    config = FactoryConfig()
    for name, ftype in field_types.items():
        config.add_field(name, ftype)
    return DataFactory(model_class, config)
