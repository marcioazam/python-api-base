"""Property-based tests for Contract Testing.

**Feature: api-architecture-analysis, Task 10.4: Contract Testing**
**Validates: Requirements 8.3**
"""

from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel

from my_app.shared.contract_testing import (
    Contract,
    ContractExpectation,
    ContractInteraction,
    ContractReport,
    ContractStatus,
    ContractTester,
    Matcher,
    MatcherType,
    OpenAPIContractValidator,
    any_value,
    contains,
    exact,
    range_match,
    regex,
    type_match,
)


class SampleRequest(BaseModel):
    """Sample request model for testing."""

    name: str
    value: int


class SampleResponse(BaseModel):
    """Sample response model for testing."""

    id: str
    name: str
    created: bool


class TestMatcherProperties:
    """Property tests for Matcher."""

    @settings(max_examples=50)
    @given(value=st.text(min_size=1, max_size=50))
    def test_exact_matcher_matches_same_value(self, value: str) -> None:
        """Exact matcher SHALL match identical values."""
        matcher = exact(value)
        assert matcher.matches(value) is True

    @settings(max_examples=50)
    @given(
        value1=st.text(min_size=1, max_size=20),
        value2=st.text(min_size=1, max_size=20),
    )
    def test_exact_matcher_rejects_different_values(self, value1: str, value2: str) -> None:
        """Exact matcher SHALL reject different values."""
        if value1 != value2:
            matcher = exact(value1)
            assert matcher.matches(value2) is False

    @settings(max_examples=30)
    @given(value=st.integers())
    def test_type_matcher_matches_correct_type(self, value: int) -> None:
        """Type matcher SHALL match values of correct type."""
        matcher = type_match(int)
        assert matcher.matches(value) is True

    @settings(max_examples=30)
    @given(value=st.text(min_size=1))
    def test_type_matcher_rejects_wrong_type(self, value: str) -> None:
        """Type matcher SHALL reject values of wrong type."""
        matcher = type_match(int)
        assert matcher.matches(value) is False

    @settings(max_examples=30)
    @given(
        min_val=st.integers(min_value=0, max_value=50),
        max_val=st.integers(min_value=51, max_value=100),
    )
    def test_range_matcher_accepts_values_in_range(self, min_val: int, max_val: int) -> None:
        """Range matcher SHALL accept values within range."""
        matcher = range_match(min_val, max_val)
        mid_val = (min_val + max_val) // 2
        assert matcher.matches(mid_val) is True

    @settings(max_examples=30)
    @given(
        min_val=st.integers(min_value=50, max_value=100),
        test_val=st.integers(min_value=0, max_value=49),
    )
    def test_range_matcher_rejects_values_below_min(self, min_val: int, test_val: int) -> None:
        """Range matcher SHALL reject values below minimum."""
        matcher = range_match(min_val=min_val)
        assert matcher.matches(test_val) is False

    def test_regex_matcher_matches_pattern(self) -> None:
        """Regex matcher SHALL match strings matching pattern."""
        matcher = regex(r"^test-\d+$")
        assert matcher.matches("test-123") is True
        assert matcher.matches("test-abc") is False

    @settings(max_examples=30)
    @given(substring=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))))
    def test_contains_matcher_finds_substring(self, substring: str) -> None:
        """Contains matcher SHALL find substring in string."""
        full_string = f"prefix-{substring}-suffix"
        matcher = contains(substring)
        assert matcher.matches(full_string) is True

    @settings(max_examples=30)
    @given(value=st.one_of(st.integers(), st.text(), st.booleans()))
    def test_any_matcher_accepts_all_values(self, value) -> None:
        """Any matcher SHALL accept any value."""
        matcher = any_value()
        assert matcher.matches(value) is True


class TestContractProperties:
    """Property tests for Contract."""

    @settings(max_examples=30)
    @given(
        name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L",))),
        consumer=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))),
        provider=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))),
    )
    def test_contract_preserves_metadata(self, name: str, consumer: str, provider: str) -> None:
        """Contract SHALL preserve name, consumer, and provider."""
        contract = Contract(name=name, consumer=consumer, provider=provider)
        assert contract.name == name
        assert contract.consumer == consumer
        assert contract.provider == provider

    @settings(max_examples=20)
    @given(num_interactions=st.integers(min_value=1, max_value=5))
    def test_contract_stores_all_interactions(self, num_interactions: int) -> None:
        """Contract SHALL store all added interactions."""
        contract = Contract(name="test", consumer="c", provider="p")
        for i in range(num_interactions):
            contract.add_interaction(
                description=f"interaction-{i}",
                method="GET",
                path=f"/path/{i}",
            )
        assert len(contract.interactions) == num_interactions

    def test_contract_serialization_round_trip(self) -> None:
        """Contract SHALL survive serialization round-trip."""
        contract = Contract(name="test-contract", consumer="frontend", provider="api")
        contract.add_interaction(
            description="Get item",
            method="GET",
            path="/items/1",
            expected_status=200,
        )
        contract.add_interaction(
            description="Create item",
            method="POST",
            path="/items",
            request_body={"name": "test"},
            expected_status=201,
        )

        data = contract.to_dict()
        restored = Contract.from_dict(data)

        assert restored.name == contract.name
        assert restored.consumer == contract.consumer
        assert restored.provider == contract.provider
        assert len(restored.interactions) == len(contract.interactions)


class TestContractTesterProperties:
    """Property tests for ContractTester."""

    def test_tester_registers_contracts(self) -> None:
        """ContractTester SHALL register and retrieve contracts."""
        tester: ContractTester[SampleRequest, SampleResponse] = ContractTester(
            request_type=SampleRequest,
            response_type=SampleResponse,
        )
        contract = Contract(name="test", consumer="c", provider="p")
        tester.register_contract(contract)

        assert tester.get_contract("test") is contract
        assert "test" in tester.list_contracts()

    def test_tester_validates_request_schema(self) -> None:
        """ContractTester SHALL validate request against schema."""
        tester: ContractTester[SampleRequest, SampleResponse] = ContractTester(
            request_type=SampleRequest,
            response_type=SampleResponse,
        )

        valid, errors = tester.validate_request({"name": "test", "value": 42})
        assert valid is True
        assert len(errors) == 0

        valid, errors = tester.validate_request({"name": "test"})
        assert valid is False
        assert len(errors) > 0

    def test_tester_validates_response_schema(self) -> None:
        """ContractTester SHALL validate response against schema."""
        tester: ContractTester[SampleRequest, SampleResponse] = ContractTester(
            request_type=SampleRequest,
            response_type=SampleResponse,
        )

        valid, errors = tester.validate_response({"id": "123", "name": "test", "created": True})
        assert valid is True
        assert len(errors) == 0

        valid, errors = tester.validate_response({"id": "123"})
        assert valid is False
        assert len(errors) > 0

    def test_verify_interaction_checks_status_code(self) -> None:
        """Verify interaction SHALL check status code."""
        tester: ContractTester[SampleRequest, SampleResponse] = ContractTester()
        interaction = ContractInteraction(
            description="test",
            request_method="GET",
            request_path="/test",
            expectation=ContractExpectation(status_code=200),
        )

        result = tester.verify_interaction(interaction, 200, {}, {})
        assert result.status == ContractStatus.PASSED

        result = tester.verify_interaction(interaction, 404, {}, {})
        assert result.status == ContractStatus.FAILED
        assert any("Status mismatch" in e for e in result.errors)

    def test_verify_interaction_checks_headers(self) -> None:
        """Verify interaction SHALL check expected headers."""
        tester: ContractTester[SampleRequest, SampleResponse] = ContractTester()
        interaction = ContractInteraction(
            description="test",
            request_method="GET",
            request_path="/test",
            expectation=ContractExpectation(
                status_code=200,
                headers={"Content-Type": exact("application/json")},
            ),
        )

        result = tester.verify_interaction(
            interaction, 200, {"Content-Type": "application/json"}, {}
        )
        assert result.status == ContractStatus.PASSED

        result = tester.verify_interaction(
            interaction, 200, {"Content-Type": "text/html"}, {}
        )
        assert result.status == ContractStatus.FAILED

    def test_verify_interaction_checks_body_matchers(self) -> None:
        """Verify interaction SHALL check body field matchers."""
        tester: ContractTester[SampleRequest, SampleResponse] = ContractTester()
        interaction = ContractInteraction(
            description="test",
            request_method="GET",
            request_path="/test",
            expectation=ContractExpectation(
                status_code=200,
                body_matchers={
                    "id": type_match(str),
                    "count": range_match(min_val=0),
                },
            ),
        )

        result = tester.verify_interaction(
            interaction, 200, {}, {"id": "abc", "count": 5}
        )
        assert result.status == ContractStatus.PASSED

        result = tester.verify_interaction(
            interaction, 200, {}, {"id": 123, "count": 5}
        )
        assert result.status == ContractStatus.FAILED

    def test_verify_contract_returns_report(self) -> None:
        """Verify contract SHALL return complete report."""
        tester: ContractTester[SampleRequest, SampleResponse] = ContractTester()
        contract = Contract(name="test", consumer="c", provider="p")
        contract.add_interaction(
            description="Get item",
            method="GET",
            path="/items/1",
            expected_status=200,
        )
        contract.add_interaction(
            description="Create item",
            method="POST",
            path="/items",
            expected_status=201,
        )
        tester.register_contract(contract)

        def mock_provider(interaction: ContractInteraction):
            if interaction.request_method == "GET":
                return 200, {}, {"id": "1"}
            return 201, {}, {"id": "2"}

        report = tester.verify_contract("test", mock_provider)

        assert report.contract_name == "test"
        assert report.total_interactions == 2
        assert report.passed == 2
        assert report.failed == 0
        assert report.all_passed is True
        assert report.success_rate == 100.0


class TestContractReportProperties:
    """Property tests for ContractReport."""

    @settings(max_examples=30)
    @given(
        passed=st.integers(min_value=0, max_value=50),
        failed=st.integers(min_value=0, max_value=50),
    )
    def test_success_rate_calculation(self, passed: int, failed: int) -> None:
        """Success rate SHALL be correctly calculated."""
        total = passed + failed
        report = ContractReport(
            contract_name="test",
            consumer="c",
            provider="p",
            total_interactions=total,
            passed=passed,
            failed=failed,
        )

        if total == 0:
            assert report.success_rate == 100.0
        else:
            expected_rate = (passed / total) * 100
            assert abs(report.success_rate - expected_rate) < 0.01

    @settings(max_examples=20)
    @given(failed=st.integers(min_value=0, max_value=10))
    def test_all_passed_property(self, failed: int) -> None:
        """all_passed SHALL be True only when failed is 0."""
        report = ContractReport(
            contract_name="test",
            consumer="c",
            provider="p",
            total_interactions=10,
            passed=10 - failed,
            failed=failed,
        )

        assert report.all_passed == (failed == 0)


class TestOpenAPIContractValidatorProperties:
    """Property tests for OpenAPIContractValidator."""

    def test_validates_documented_paths(self) -> None:
        """Validator SHALL accept documented paths."""
        spec = {
            "paths": {
                "/items": {
                    "get": {"responses": {"200": {}}},
                    "post": {"responses": {"201": {}}},
                },
                "/items/{id}": {
                    "get": {"responses": {"200": {}}},
                },
            }
        }
        validator = OpenAPIContractValidator(spec)

        interaction = ContractInteraction(
            description="test",
            request_method="GET",
            request_path="/items",
            expectation=ContractExpectation(status_code=200),
        )
        valid, errors = validator.validate_interaction(interaction)
        assert valid is True

    def test_rejects_undocumented_paths(self) -> None:
        """Validator SHALL reject undocumented paths."""
        spec = {"paths": {"/items": {"get": {"responses": {"200": {}}}}}}
        validator = OpenAPIContractValidator(spec)

        interaction = ContractInteraction(
            description="test",
            request_method="GET",
            request_path="/unknown",
            expectation=ContractExpectation(status_code=200),
        )
        valid, errors = validator.validate_interaction(interaction)
        assert valid is False
        assert any("not found" in e for e in errors)

    def test_rejects_undocumented_methods(self) -> None:
        """Validator SHALL reject undocumented methods."""
        spec = {"paths": {"/items": {"get": {"responses": {"200": {}}}}}}
        validator = OpenAPIContractValidator(spec)

        interaction = ContractInteraction(
            description="test",
            request_method="DELETE",
            request_path="/items",
            expectation=ContractExpectation(status_code=200),
        )
        valid, errors = validator.validate_interaction(interaction)
        assert valid is False
        assert any("not allowed" in e for e in errors)

    def test_generates_contract_from_spec(self) -> None:
        """Validator SHALL generate contract from OpenAPI spec."""
        spec = {
            "paths": {
                "/items": {
                    "get": {"summary": "List items", "responses": {"200": {}}},
                    "post": {"summary": "Create item", "responses": {"201": {}}},
                },
            }
        }
        validator = OpenAPIContractValidator(spec)

        contract = validator.generate_contract_from_spec(
            consumer="frontend",
            provider="api",
        )

        assert contract.consumer == "frontend"
        assert contract.provider == "api"
        assert len(contract.interactions) == 2
