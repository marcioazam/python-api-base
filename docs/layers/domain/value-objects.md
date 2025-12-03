# Value Objects

## Overview

Value Objects são objetos imutáveis definidos por seus atributos, sem identidade própria. Dois value objects são iguais se todos os seus atributos são iguais.

## Characteristics

- **Imutáveis** - Não podem ser modificados após criação
- **Sem identidade** - Igualdade por valor, não por referência
- **Auto-validantes** - Validam no construtor
- **Substituíveis** - Podem ser trocados por outro com mesmo valor

## Basic Value Object

```python
from dataclasses import dataclass
import re

@dataclass(frozen=True, slots=True)
class Email:
    """Email value object with validation."""
    
    value: str
    
    def __post_init__(self) -> None:
        if not self._is_valid(self.value):
            raise ValueError(f"Invalid email: {self.value}")
    
    @staticmethod
    def _is_valid(email: str) -> bool:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
    
    @property
    def domain(self) -> str:
        return self.value.split("@")[1]
    
    @property
    def local_part(self) -> str:
        return self.value.split("@")[0]
```

## Money Value Object

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True, slots=True)
class Money:
    """Money value object with currency."""
    
    amount: Decimal
    currency: str
    
    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be 3-letter ISO code")
    
    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)
    
    def subtract(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return Money(self.amount - other.amount, self.currency)
    
    def multiply(self, factor: Decimal) -> "Money":
        return Money(self.amount * factor, self.currency)
    
    def __str__(self) -> str:
        return f"{self.currency} {self.amount:.2f}"
```

## Address Value Object

```python
@dataclass(frozen=True, slots=True)
class Address:
    """Address value object."""
    
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    
    def __post_init__(self) -> None:
        if not self.street:
            raise ValueError("Street is required")
        if not self.city:
            raise ValueError("City is required")
        if not self.postal_code:
            raise ValueError("Postal code is required")
    
    @property
    def full_address(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.postal_code}, {self.country}"
```

## DateRange Value Object

```python
from datetime import date

@dataclass(frozen=True, slots=True)
class DateRange:
    """Date range value object."""
    
    start: date
    end: date
    
    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("Start date must be before end date")
    
    def contains(self, d: date) -> bool:
        return self.start <= d <= self.end
    
    def overlaps(self, other: "DateRange") -> bool:
        return self.start <= other.end and other.start <= self.end
    
    @property
    def days(self) -> int:
        return (self.end - self.start).days
```

## Password Value Object

```python
import hashlib
import secrets

@dataclass(frozen=True, slots=True)
class Password:
    """Password value object with hashing."""
    
    hash: str
    
    @classmethod
    def create(cls, plain_text: str) -> "Password":
        """Create password from plain text."""
        if len(plain_text) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        salt = secrets.token_hex(16)
        hash_value = hashlib.pbkdf2_hmac(
            "sha256",
            plain_text.encode(),
            salt.encode(),
            100000,
        ).hex()
        
        return cls(hash=f"{salt}${hash_value}")
    
    def verify(self, plain_text: str) -> bool:
        """Verify password against hash."""
        salt, stored_hash = self.hash.split("$")
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_text.encode(),
            salt.encode(),
            100000,
        ).hex()
        return secrets.compare_digest(stored_hash, computed_hash)
```

## Usage in Entities

```python
@dataclass
class User:
    id: str
    email: Email  # Value object
    password: Password  # Value object
    name: str
    
    @classmethod
    def create(cls, email: str, password: str, name: str) -> "User":
        return cls(
            id=str(ULID()),
            email=Email(email),  # Validates email
            password=Password.create(password),  # Hashes password
            name=name,
        )
```

## Best Practices

1. **Use `frozen=True`** - Ensures immutability
2. **Use `slots=True`** - Memory efficiency
3. **Validate in `__post_init__`** - Fail fast
4. **Return new instances** - Never mutate
5. **Keep simple** - Single responsibility
