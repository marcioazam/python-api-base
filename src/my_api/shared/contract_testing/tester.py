"""Contract tester implementation.

**Feature: code-review-refactoring, Task 17.1: Refactor contract_testing.py**
**Validates: Requirements 5.4**
"""

from datetime import datetime, UTC
from typing import Any
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from .contract import Contract, ContractInteraction
from .enums import ContractStatus
from .report import ContractReport, ContractVerificationResult


class ContractTester[RequestT: BaseModel, ResponseT: BaseModel]:
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

    def register_contract(
        self, contract: Contract
    ) -> "ContractTester[RequestT, ResponseT]":
        """Register a contract for testing."""
        self._contracts[contract.name] = contract
        return self

    def set_http_client(
        self, client: Callable[..., Any]
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
        start_time = datetime.now(UTC)
        errors: list[str] = []

        if actual_status != interaction.expectation.status_code:
            errors.append(
                f"Status mismatch: expected {interaction.expectation.status_code}, "
                f"got {actual_status}"
            )

        for header_name, matcher in interaction.expectation.headers.items():
            actual_value = actual_headers.get(header_name)
            if actual_value is None:
                errors.append(f"Missing header: {header_name}")
            elif not matcher.matches(actual_value):
                errors.append(
                    f"Header '{header_name}' mismatch: expected {matcher.expected}, "
                    f"got {actual_value}"
                )

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

        if interaction.expectation.body_schema and isinstance(actual_body, dict):
            try:
                interaction.expectation.body_schema.model_validate(actual_body)
            except ValidationError as e:
                for err in e.errors():
                    errors.append(f"Schema validation: {err['loc']} - {err['msg']}")

        duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
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
        response_provider: Callable[
            [ContractInteraction], tuple[int, dict[str, str], Any]
        ],
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
