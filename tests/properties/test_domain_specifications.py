"""Property-based tests for Specification pattern composition.

**Feature: domain-specification-properties**
**Validates: Composition laws, logical properties, type safety**

Tests verify that Specification composition follows:
- Associativity: (A & B) & C == A & (B & C)
- Commutativity: A & B == B & A (for AND/OR)
- Identity: A & True == A, A | False == A
- Absorption: A & (A | B) == A, A | (A & B) == A
- De Morgan's laws: ~(A & B) == (~A) | (~B)
- Double negation: ~~A == A
- Idempotency: A & A == A, A | A == A
- Distributivity: A & (B | C) == (A & B) | (A & C)
"""

import pytest
from dataclasses import dataclass
from hypothesis import given, strategies as st

from src.domain.common.specification.specification import (
    Specification,
    PredicateSpecification,
    spec,
    AndSpecification,
    OrSpecification,
    NotSpecification,
)


# Test domain models
@dataclass
class Person:
    """Test entity for specifications."""

    name: str
    age: int
    is_active: bool
    score: float


# Helper to create test specifications
def is_adult() -> Specification[Person]:
    """Specification: person is 18 or older."""
    return spec(lambda p: p.age >= 18, "is_adult")


def is_senior() -> Specification[Person]:
    """Specification: person is 65 or older."""
    return spec(lambda p: p.age >= 65, "is_senior")


def is_active() -> Specification[Person]:
    """Specification: person is active."""
    return spec(lambda p: p.is_active, "is_active")


def has_high_score() -> Specification[Person]:
    """Specification: person has score >= 80."""
    return spec(lambda p: p.score >= 80, "has_high_score")


def always_true() -> Specification[Person]:
    """Specification that always returns True."""
    return spec(lambda _: True, "always_true")


def always_false() -> Specification[Person]:
    """Specification that always returns False."""
    return spec(lambda _: False, "always_false")


# Hypothesis strategies for test data
@st.composite
def person_strategy(draw):
    """Strategy to generate Person instances."""
    name = draw(st.text(min_size=1, max_size=50))
    age = draw(st.integers(min_value=0, max_value=120))
    is_active = draw(st.booleans())
    score = draw(st.floats(min_value=0.0, max_value=100.0))
    return Person(name=name, age=age, is_active=is_active, score=score)


class TestSpecificationCommutativity:
    """Tests for commutative properties of AND and OR."""

    @given(person_strategy())
    def test_and_commutativity(self, person: Person) -> None:
        """Property: A & B == B & A."""
        spec_a = is_adult()
        spec_b = is_active()

        # Create compositions
        a_and_b = spec_a & spec_b
        b_and_a = spec_b & spec_a

        # Verify commutativity
        assert a_and_b.is_satisfied_by(person) == b_and_a.is_satisfied_by(person)

    @given(person_strategy())
    def test_or_commutativity(self, person: Person) -> None:
        """Property: A | B == B | A."""
        spec_a = is_adult()
        spec_b = is_active()

        # Create compositions
        a_or_b = spec_a | spec_b
        b_or_a = spec_b | spec_a

        # Verify commutativity
        assert a_or_b.is_satisfied_by(person) == b_or_a.is_satisfied_by(person)


class TestSpecificationAssociativity:
    """Tests for associative properties of AND and OR."""

    @given(person_strategy())
    def test_and_associativity(self, person: Person) -> None:
        """Property: (A & B) & C == A & (B & C)."""
        spec_a = is_adult()
        spec_b = is_active()
        spec_c = has_high_score()

        # Create different groupings
        left_grouped = (spec_a & spec_b) & spec_c
        right_grouped = spec_a & (spec_b & spec_c)

        # Verify associativity
        assert left_grouped.is_satisfied_by(person) == right_grouped.is_satisfied_by(
            person
        )

    @given(person_strategy())
    def test_or_associativity(self, person: Person) -> None:
        """Property: (A | B) | C == A | (B | C)."""
        spec_a = is_adult()
        spec_b = is_active()
        spec_c = has_high_score()

        # Create different groupings
        left_grouped = (spec_a | spec_b) | spec_c
        right_grouped = spec_a | (spec_b | spec_c)

        # Verify associativity
        assert left_grouped.is_satisfied_by(person) == right_grouped.is_satisfied_by(
            person
        )


class TestSpecificationIdentity:
    """Tests for identity laws."""

    @given(person_strategy())
    def test_and_identity_true(self, person: Person) -> None:
        """Property: A & True == A."""
        spec_a = is_adult()
        true_spec = always_true()

        # Combine with True
        a_and_true = spec_a & true_spec

        # Verify identity: result should match A alone
        assert a_and_true.is_satisfied_by(person) == spec_a.is_satisfied_by(person)

    @given(person_strategy())
    def test_or_identity_false(self, person: Person) -> None:
        """Property: A | False == A."""
        spec_a = is_adult()
        false_spec = always_false()

        # Combine with False
        a_or_false = spec_a | false_spec

        # Verify identity: result should match A alone
        assert a_or_false.is_satisfied_by(person) == spec_a.is_satisfied_by(person)

    @given(person_strategy())
    def test_and_annihilation_false(self, person: Person) -> None:
        """Property: A & False == False."""
        spec_a = is_adult()
        false_spec = always_false()

        # Combine with False
        a_and_false = spec_a & false_spec

        # Verify annihilation: result should always be False
        assert a_and_false.is_satisfied_by(person) is False

    @given(person_strategy())
    def test_or_annihilation_true(self, person: Person) -> None:
        """Property: A | True == True."""
        spec_a = is_adult()
        true_spec = always_true()

        # Combine with True
        a_or_true = spec_a | true_spec

        # Verify annihilation: result should always be True
        assert a_or_true.is_satisfied_by(person) is True


class TestSpecificationAbsorption:
    """Tests for absorption laws."""

    @given(person_strategy())
    def test_and_absorption(self, person: Person) -> None:
        """Property: A & (A | B) == A."""
        spec_a = is_adult()
        spec_b = is_active()

        # Create absorption composition
        absorbed = spec_a & (spec_a | spec_b)

        # Verify absorption: result should match A alone
        assert absorbed.is_satisfied_by(person) == spec_a.is_satisfied_by(person)

    @given(person_strategy())
    def test_or_absorption(self, person: Person) -> None:
        """Property: A | (A & B) == A."""
        spec_a = is_adult()
        spec_b = is_active()

        # Create absorption composition
        absorbed = spec_a | (spec_a & spec_b)

        # Verify absorption: result should match A alone
        assert absorbed.is_satisfied_by(person) == spec_a.is_satisfied_by(person)


class TestSpecificationDeMorganLaws:
    """Tests for De Morgan's laws."""

    @given(person_strategy())
    def test_de_morgan_and(self, person: Person) -> None:
        """Property: ~(A & B) == (~A) | (~B)."""
        spec_a = is_adult()
        spec_b = is_active()

        # De Morgan's law for AND
        not_a_and_b = ~(spec_a & spec_b)
        not_a_or_not_b = (~spec_a) | (~spec_b)

        # Verify equivalence
        assert not_a_and_b.is_satisfied_by(person) == not_a_or_not_b.is_satisfied_by(
            person
        )

    @given(person_strategy())
    def test_de_morgan_or(self, person: Person) -> None:
        """Property: ~(A | B) == (~A) & (~B)."""
        spec_a = is_adult()
        spec_b = is_active()

        # De Morgan's law for OR
        not_a_or_b = ~(spec_a | spec_b)
        not_a_and_not_b = (~spec_a) & (~spec_b)

        # Verify equivalence
        assert not_a_or_b.is_satisfied_by(person) == not_a_and_not_b.is_satisfied_by(
            person
        )


class TestSpecificationNegation:
    """Tests for negation properties."""

    @given(person_strategy())
    def test_double_negation(self, person: Person) -> None:
        """Property: ~~A == A."""
        spec_a = is_adult()

        # Double negation
        double_negated = ~~spec_a

        # Verify equivalence
        assert double_negated.is_satisfied_by(person) == spec_a.is_satisfied_by(person)

    @given(person_strategy())
    def test_negation_inverts(self, person: Person) -> None:
        """Property: ~A inverts the result of A."""
        spec_a = is_adult()
        not_a = ~spec_a

        # Verify inversion
        assert not_a.is_satisfied_by(person) == (not spec_a.is_satisfied_by(person))

    @given(person_strategy())
    def test_contradiction(self, person: Person) -> None:
        """Property: A & ~A == False."""
        spec_a = is_adult()

        # Contradiction
        contradiction = spec_a & (~spec_a)

        # Verify always False
        assert contradiction.is_satisfied_by(person) is False

    @given(person_strategy())
    def test_excluded_middle(self, person: Person) -> None:
        """Property: A | ~A == True."""
        spec_a = is_adult()

        # Excluded middle
        excluded_middle = spec_a | (~spec_a)

        # Verify always True
        assert excluded_middle.is_satisfied_by(person) is True


class TestSpecificationIdempotency:
    """Tests for idempotent properties."""

    @given(person_strategy())
    def test_and_idempotency(self, person: Person) -> None:
        """Property: A & A == A."""
        spec_a = is_adult()

        # Idempotent AND
        a_and_a = spec_a & spec_a

        # Verify equivalence
        assert a_and_a.is_satisfied_by(person) == spec_a.is_satisfied_by(person)

    @given(person_strategy())
    def test_or_idempotency(self, person: Person) -> None:
        """Property: A | A == A."""
        spec_a = is_adult()

        # Idempotent OR
        a_or_a = spec_a | spec_a

        # Verify equivalence
        assert a_or_a.is_satisfied_by(person) == spec_a.is_satisfied_by(person)


class TestSpecificationDistributivity:
    """Tests for distributive laws."""

    @given(person_strategy())
    def test_and_distributes_over_or(self, person: Person) -> None:
        """Property: A & (B | C) == (A & B) | (A & C)."""
        spec_a = is_adult()
        spec_b = is_active()
        spec_c = has_high_score()

        # Distributive law
        left = spec_a & (spec_b | spec_c)
        right = (spec_a & spec_b) | (spec_a & spec_c)

        # Verify equivalence
        assert left.is_satisfied_by(person) == right.is_satisfied_by(person)

    @given(person_strategy())
    def test_or_distributes_over_and(self, person: Person) -> None:
        """Property: A | (B & C) == (A | B) & (A | C)."""
        spec_a = is_adult()
        spec_b = is_active()
        spec_c = has_high_score()

        # Distributive law
        left = spec_a | (spec_b & spec_c)
        right = (spec_a | spec_b) & (spec_a | spec_c)

        # Verify equivalence
        assert left.is_satisfied_by(person) == right.is_satisfied_by(person)


class TestSpecificationComposition:
    """Tests for complex specification compositions."""

    @given(person_strategy())
    def test_complex_composition(self, person: Person) -> None:
        """Test complex composition: (Adult & Active) | (Senior & HighScore)."""
        # Business rule: Either (adult and active) OR (senior and high score)
        adult_and_active = is_adult() & is_active()
        senior_and_high_score = is_senior() & has_high_score()
        complex_spec = adult_and_active | senior_and_high_score

        # Manual evaluation
        expected = (person.age >= 18 and person.is_active) or (
            person.age >= 65 and person.score >= 80
        )

        # Verify
        assert complex_spec.is_satisfied_by(person) == expected

    @given(person_strategy())
    def test_nested_negations(self, person: Person) -> None:
        """Test nested negations: ~(Adult & ~Active)."""
        # Business rule: NOT (adult AND NOT active)
        # Equivalent to: NOT adult OR active (by De Morgan's)
        nested = ~(is_adult() & ~is_active())

        # Manual evaluation
        expected = not (person.age >= 18 and not person.is_active)

        # Verify
        assert nested.is_satisfied_by(person) == expected

    @given(person_strategy())
    def test_multiple_operators(self, person: Person) -> None:
        """Test using multiple operators: (A & B) | (~C)."""
        complex_spec = (is_adult() & is_active()) | (~has_high_score())

        # Manual evaluation
        expected = (person.age >= 18 and person.is_active) or (not person.score >= 80)

        # Verify
        assert complex_spec.is_satisfied_by(person) == expected


class TestSpecificationTypeInvariance:
    """Tests that specifications maintain type invariance."""

    def test_type_consistency_with_and(self) -> None:
        """Test that AND composition preserves type."""
        spec_a: Specification[Person] = is_adult()
        spec_b: Specification[Person] = is_active()

        # Compose - should be Specification[Person]
        composed: Specification[Person] = spec_a & spec_b

        # Verify type is preserved
        assert isinstance(composed, AndSpecification)

    def test_type_consistency_with_or(self) -> None:
        """Test that OR composition preserves type."""
        spec_a: Specification[Person] = is_adult()
        spec_b: Specification[Person] = is_active()

        # Compose - should be Specification[Person]
        composed: Specification[Person] = spec_a | spec_b

        # Verify type is preserved
        assert isinstance(composed, OrSpecification)

    def test_type_consistency_with_not(self) -> None:
        """Test that NOT preserves type."""
        spec_a: Specification[Person] = is_adult()

        # Negate - should be Specification[Person]
        negated: Specification[Person] = ~spec_a

        # Verify type is preserved
        assert isinstance(negated, NotSpecification)


class TestSpecificationEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_specification_with_none_candidate(self) -> None:
        """Test specification behavior with None candidate."""
        spec_a = is_adult()

        # This will raise AttributeError because None has no 'age'
        with pytest.raises(AttributeError):
            spec_a.is_satisfied_by(None)  # type: ignore

    @given(person_strategy())
    def test_deeply_nested_composition(self, person: Person) -> None:
        """Test deeply nested specification composition."""
        # Create deeply nested: (((A & B) | C) & D)
        deeply_nested = (((is_adult() & is_active()) | has_high_score()) & is_senior())

        # Should still evaluate correctly
        result = deeply_nested.is_satisfied_by(person)
        assert isinstance(result, bool)

    def test_specification_factory_function(self) -> None:
        """Test the spec() factory function."""
        # Create specification using factory
        custom_spec = spec(lambda p: p.age > 25 and p.score > 50, "custom")

        person = Person(name="Test", age=30, is_active=True, score=60)
        assert custom_spec.is_satisfied_by(person) is True

        young_person = Person(name="Young", age=20, is_active=True, score=60)
        assert custom_spec.is_satisfied_by(young_person) is False
