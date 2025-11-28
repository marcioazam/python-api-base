"""Contract Testing - API contract validation for consumer-driven contracts.

**Feature: api-architecture-analysis, Task 10.4: Contract Testing**
**Validates: Requirements 8.3**

Provides:
- ContractTester[RequestT, ResponseT] for type-safe contract validation
- Contract definition and verification
- Schema validation against OpenAPI specs
- Consumer-driven contract testing support
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel, ValidationError


RequestT = TypeVar("RequestT", bound=BaseModel)
ResponseT = TypeVar("ResponseT", bound=BaseModel)


class ContractStatus(str, Enum):
    """Status of a contract verification."""

    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
    SKIPPED = "skipped"


class MatcherType(str, Enum):
    """Types of matchers for contract validation."""

    EXACT = "exact"
    TYPE = "type"
    REGEX = "regex"
    RANGE = "range"
    CONTAINS = "contains"
    ANY = "any"


@dataclass
class Matcher:
    """A matcher for validating values in contracts."""

    matcher_type: MatcherType
    expected: Any = None
    min_value: Any = None
    max_value: Any = None
    pattern: str | None = None

    def matches(self, actual: Any) -> bool:
        """Check if actual value matches the expectation."""
        if self.matcher_type == MatcherType.EXACT:
            return actual == self.expected
        elif self.matcher_type == MatcherType.TYPE:
            return isinstance(actual, self.expected)
        elif self.matcher_type == MatcherType.REGEX:
            if self.pattern and isinstance(actual, str):
                return bool(re.match(self.pattern, actual))
            return False
        elif self.matcher_type == MatcherType.RANGE:
            if self.min_value is not None and actual < self.min_value:
                return False
            if self.max_value is not None and actual > self.max_value:
                return False
            return True
        elif self.matcher_type == MatcherType.CONTAINS:
            if isinstance(actual, (str, list, dict)):
                return self.expected in actual
            return False
        elif self.matcher_type == MatcherType.ANY:
            return True
        return False


@dataclass
class ContractExpectation:
    """Expected values for a contract interaction."""

    status_code: int = 200
    headers: dict[str, Matcher] = field(default_factory=dict)
    body_matchers: dict[str, Matcher] = field(default_factory=dict)
    body_schema: type[BaseModel] | None = None


@dataclass
class ContractInteraction:
    """A single interaction in a contract."""

    description: str
    request_method: str
    request_path: str
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: Any = None
    expectation: ContractExpectation = field(default_factory=ContractExpectation)


@dataclass
class ContractVerificationResult:
    """Result of verifying a single interaction."""

    interaction: str
    status: ContractStatus
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ContractReport:
    """Full report of contract verification."""

    contract_name: str
    consumer: str
    provider: str
    results: list[ContractVerificationResult] = field(default_factory=list)
    total_interactions: int = 0
    passed: int = 0
    failed: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_interactions == 0:
            return 100.0
        return (self.passed / self.total_interactions) * 100

    @property
    def all_passed(self) -> bool:
        """Check if all interactions passed."""
        return self.failed == 0


class Contract:
    """Definition of an API contract between consumer and provider."""

    def __init__(
        self,
        name: str,
        consumer: str,
        provider: str,
    ) -> None:
        """Initialize contract."""
        self.name = name
        self.consumer = consumer
        self.provider = provider
        self.interactions: list[ContractInteraction] = []
        self.metadata: dict[str, Any] = {}

    def add_interaction(
        self,
        description: str,
        method: str,
        path: str,
        request_headers: dict[str, str] | None = None,
        request_body: Any = None,
        expected_status: int = 200,
        expected_headers: dict[str, Matcher] | None = None,
        expected_body_matchers: dict[str, Matcher] | None = None,
        expected_body_schema: type[BaseModel] | None = None,
    ) -> "Contract":
        """Add an interaction to the contract."""
        expectation = ContractExpectation(
            status_code=expected_status,
            headers=expected_headers or {},
            body_matchers=expected_body_matchers or {},
            body_schema=expected_body_schema,
        )
        interaction = ContractInteraction(
            description=description,
            request_method=method.upper(),
            request_path=path,
            request_headers=request_headers or {},
            request_body=request_body,
            expectation=expectation,
        )
        self.interactions.append(interaction)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert contract to dictionary for serialization."""
        return {
            "name": self.name,
            "consumer": self.consumer,
            "provider": self.provider,
            "interactions": [
                {
                    "description": i.description,
                    "request": {
                        "method": i.request_method,
                        "path": i.request_path,
                        "headers": i.request_headers,
                        "body": i.request_body,
                    },
                    "response": {
                        "status": i.expectation.status_code,
                    },
                }
                for i in self.interactions
            ],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Contract":
        """Create contract from dictionary."""
        contract = cls(
            name=data["name"],
            consumer=data["consumer"],
            provider=data["provider"],
        )
        contract.metadata = data.get("metadata", {})
        for interaction_data in data.get("interactions", []):
            request = interaction_data.get("request", {})
            response = interaction_data.get("response", {})
            contract.add_interaction(
                description=interaction_data.get("description", ""),
                method=request.get("method", "GET"),
                path=request.get("path", "/"),
                request_headers=request.get("headers"),
                request_body=request.get("body"),
                expected_status=response.get("status", 200),
            )
        return contract


class ContractTester(Generic[RequestT, ResponseT]):
    """Generic contract tester for API validation."""

    def __init__(
        self,
        request_type: type[RequestT] | None = None,
        response_type: type[ResponseT] | None = None,
    ) -> None:
        """Initialize contract tester."""
        self._request_type = request_type
        self._response_type = response_type
        self._contracts: dict[str, Contract] = {}
        self._http_client: Callable[..., Any] | None = None

    def register_contract(self, contract: Contract) -> "ContractTester[RequestT, ResponseT]":
        """Register a contract for testing."""
        self._contracts[contract.name] = contract
        return self

    def set_http_client(
        self,
        client: Callable[..., Any],
    ) -> "ContractTester[RequestT, ResponseT]":
        """Set HTTP client for making requests."""
        self._http_client = client
        return self

    def validate_request(self, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate request data against request type."""
        if self._request_type is None:
            return True, []
        try:
            self._request_type.model_validate(data)
            return True, []
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return False, errors

    def validate_response(self, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate response data against response type."""
        if self._response_type is None:
            return True, []
        try:
            self._response_type.model_validate(data)
            return True, []
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return False, errors

    def verify_interaction(
        self,
        interaction: ContractInteraction,
        actual_status: int,
        actual_headers: dict[str, str],
        actual_body: Any,
    ) -> ContractVerificationResult:
        """Verify a single interaction against actual response."""
        start_time = datetime.now()
        errors: list[str] = []

        # Verify status code
        if actual_status != interaction.expectation.status_code:
            errors.append(
                f"Status mismatch: expected {interaction.expectation.status_code}, "
                f"got {actual_status}"
            )

        # Verify headers
        for header_name, matcher in interaction.expectation.headers.items():
            actual_value = actual_headers.get(header_name)
            if actual_value is None:
                errors.append(f"Missing header: {header_name}")
            elif not matcher.matches(actual_value):
                errors.append(
                    f"Header '{header_name}' mismatch: expected {matcher.expected}, "
                    f"got {actual_value}"
                )

        # Verify body with matchers
        if isinstance(actual_body, dict):
            for field_path, matcher in interaction.expectation.body_matchers.items():
                actual_value = self._get_nested_value(actual_body, field_path)
                if actual_value is None:
                    errors.append(f"Missing field: {field_path}")
                elif not matcher.matches(actual_value):
                    errors.append(
                        f"Field '{field_path}' mismatch: "
                        f"expected {matcher.matcher_type.value}, got {actual_value}"
                    )

        # Verify body schema
        if interaction.expectation.body_schema and isinstance(actual_body, dict):
            try:
                interaction.expectation.body_schema.model_validate(actual_body)
            except ValidationError as e:
                for err in e.errors():
                    errors.append(f"Schema validation: {err['loc']} - {err['msg']}")

        duration = (datetime.now() - start_time).total_seconds() * 1000
        status = ContractStatus.PASSED if not errors else ContractStatus.FAILED

        return ContractVerificationResult(
            interaction=interaction.description,
            status=status,
            errors=errors,
            duration_ms=duration,
        )

    def _get_nested_value(self, data: dict[str, Any], path: str) -> Any:
        """Get nested value from dict using dot notation."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                idx = int(key)
                value = value[idx] if idx < len(value) else None
            else:
                return None
        return value

    def verify_contract(
        self,
        contract_name: str,
        response_provider: Callable[[ContractInteraction], tuple[int, dict[str, str], Any]],
    ) -> ContractReport:
        """Verify all interactions in a contract."""
        contract = self._contracts.get(contract_name)
        if contract is None:
            return ContractReport(
                contract_name=contract_name,
                consumer="unknown",
                provider="unknown",
                results=[
                    ContractVerificationResult(
                        interaction="contract_lookup",
                        status=ContractStatus.FAILED,
                        errors=[f"Contract '{contract_name}' not found"],
                    )
                ],
                total_interactions=1,
                failed=1,
            )

        results: list[ContractVerificationResult] = []
        for interaction in contract.interactions:
            status, headers, body = response_provider(interaction)
            result = self.verify_interaction(interaction, status, headers, body)
            results.append(result)

        passed = sum(1 for r in results if r.status == ContractStatus.PASSED)
        failed = sum(1 for r in results if r.status == ContractStatus.FAILED)

        return ContractReport(
            contract_name=contract.name,
            consumer=contract.consumer,
            provider=contract.provider,
            results=results,
            total_interactions=len(results),
            passed=passed,
            failed=failed,
        )

    def get_contract(self, name: str) -> Contract | None:
        """Get a registered contract by name."""
        return self._contracts.get(name)

    def list_contracts(self) -> list[str]:
        """List all registered contract names."""
        return list(self._contracts.keys())


class OpenAPIContractValidator:
    """Validate contracts against OpenAPI specifications."""

    def __init__(self, openapi_spec: dict[str, Any]) -> None:
        """Initialize with OpenAPI spec."""
        self._spec = openapi_spec
        self._paths = openapi_spec.get("paths", {})

    def validate_interaction(
        self,
        interaction: ContractInteraction,
    ) -> tuple[bool, list[str]]:
        """Validate interaction against OpenAPI spec."""
        errors: list[str] = []

        # Find matching path in spec
        path_spec = self._find_path_spec(interaction.request_path)
        if path_spec is None:
            errors.append(f"Path '{interaction.request_path}' not found in OpenAPI spec")
            return False, errors

        # Find method spec
        method_spec = path_spec.get(interaction.request_method.lower())
        if method_spec is None:
            errors.append(
                f"Method '{interaction.request_method}' not allowed for "
                f"path '{interaction.request_path}'"
            )
            return False, errors

        # Validate response status is documented
        responses = method_spec.get("responses", {})
        status_str = str(interaction.expectation.status_code)
        if status_str not in responses and "default" not in responses:
            errors.append(
                f"Status code {interaction.expectation.status_code} not documented "
                f"for {interaction.request_method} {interaction.request_path}"
            )

        return len(errors) == 0, errors

    def _find_path_spec(self, path: str) -> dict[str, Any] | None:
        """Find path spec, handling path parameters."""
        # Try exact match first
        if path in self._paths:
            return self._paths[path]

        # Try pattern matching for path parameters
        for spec_path, spec in self._paths.items():
            pattern = re.sub(r"\{[^}]+\}", r"[^/]+", spec_path)
            if re.fullmatch(pattern, path):
                return spec

        return None

    def generate_contract_from_spec(
        self,
        consumer: str,
        provider: str,
        paths: list[str] | None = None,
    ) -> Contract:
        """Generate a contract from OpenAPI spec."""
        contract = Contract(
            name=f"{consumer}-{provider}-contract",
            consumer=consumer,
            provider=provider,
        )

        target_paths = paths or list(self._paths.keys())

        for path in target_paths:
            path_spec = self._paths.get(path, {})
            for method, method_spec in path_spec.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    responses = method_spec.get("responses", {})
                    # Use first success response
                    for status in ["200", "201", "204"]:
                        if status in responses:
                            contract.add_interaction(
                                description=method_spec.get("summary", f"{method.upper()} {path}"),
                                method=method.upper(),
                                path=path,
                                expected_status=int(status),
                            )
                            break

        return contract


# Convenience functions for creating matchers
def exact(value: Any) -> Matcher:
    """Create exact match matcher."""
    return Matcher(MatcherType.EXACT, expected=value)


def type_match(expected_type: type) -> Matcher:
    """Create type match matcher."""
    return Matcher(MatcherType.TYPE, expected=expected_type)


def regex(pattern: str) -> Matcher:
    """Create regex match matcher."""
    return Matcher(MatcherType.REGEX, pattern=pattern)


def range_match(min_val: Any = None, max_val: Any = None) -> Matcher:
    """Create range match matcher."""
    return Matcher(MatcherType.RANGE, min_value=min_val, max_value=max_val)


def contains(value: Any) -> Matcher:
    """Create contains matcher."""
    return Matcher(MatcherType.CONTAINS, expected=value)


def any_value() -> Matcher:
    """Create any value matcher."""
    return Matcher(MatcherType.ANY)
