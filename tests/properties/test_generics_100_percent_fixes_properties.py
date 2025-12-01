"""Property-based tests for Generics 100% Fixes.

**Feature: generics-100-percent-fixes**
**Validates: All correctness properties from design document**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import Optional
from dataclasses import dataclass

# Import modules under test
from my_app.infrastructure.i18n.generics import (
    Locale,
    LocalizedValue,
    DictMessageFormatter,
    EnglishPluralRules,
    PortuguesePluralRules,
    RussianPluralRules,
    TranslationCatalog,
    EN_US,
    PT_BR,
    ES_ES,
    FR_FR,
)
from my_app.core.di.container import (
    Container,
    Lifetime,
    DependencyResolutionError,
    CircularDependencyError,
    InvalidFactoryError,
    ServiceNotRegisteredError,
)


# =============================================================================
# Strategies
# =============================================================================


locale_strategy = st.sampled_from([EN_US, PT_BR, ES_ES, FR_FR])

safe_text_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters="{}"
    ),
    min_size=1,
    max_size=100,
)


# =============================================================================
# Property 2: LocalizedValue Round-Trip
# =============================================================================


@given(st.text(min_size=1, max_size=100), locale_strategy)
@settings(max_examples=100)
def test_localized_value_round_trip(value: str, locale: Locale):
    """
    **Feature: generics-100-percent-fixes, Property 2: LocalizedValue Round-Trip**
    **Validates: Requirements 2.3**
    
    For any value T and locale, creating LocalizedValue[T] and accessing
    value should return the original value unchanged.
    """
    localized = LocalizedValue(value=value, locale=locale)
    
    assert localized.value == value
    assert localized.locale == locale


@given(st.integers(), locale_strategy)
@settings(max_examples=100)
def test_localized_value_round_trip_int(value: int, locale: Locale):
    """
    **Feature: generics-100-percent-fixes, Property 2: LocalizedValue Round-Trip**
    **Validates: Requirements 2.3**
    
    Test with integer values.
    """
    localized = LocalizedValue(value=value, locale=locale)
    
    assert localized.value == value
    assert localized.locale == locale


@given(st.text(min_size=1, max_size=100), locale_strategy, locale_strategy)
@settings(max_examples=100)
def test_localized_value_with_locale(value: str, locale1: Locale, locale2: Locale):
    """
    **Feature: generics-100-percent-fixes, Property 2: LocalizedValue Round-Trip**
    **Validates: Requirements 2.3**
    
    Test with_locale preserves value.
    """
    localized = LocalizedValue(value=value, locale=locale1)
    changed = localized.with_locale(locale2)
    
    assert changed.value == value
    assert changed.locale == locale2


# =============================================================================
# Property 3: MessageFormatter Placeholder Substitution
# =============================================================================


@given(
    st.text(min_size=1, max_size=50),
    st.text(min_size=1, max_size=50),
    st.text(min_size=1, max_size=50),
)
@settings(max_examples=100)
def test_message_formatter_placeholder_substitution(
    key1: str,
    value1: str,
    value2: str,
):
    """
    **Feature: generics-100-percent-fixes, Property 3: MessageFormatter Placeholder Substitution**
    **Validates: Requirements 2.2**
    
    For any template with N placeholders and N values, formatting should
    produce a string with all placeholders replaced.
    """
    # Avoid keys with special characters
    assume("{" not in key1 and "}" not in key1)
    assume("{" not in value1 and "}" not in value1)
    assume("{" not in value2 and "}" not in value2)
    
    formatter = DictMessageFormatter()
    template = f"Hello {{{key1}}}, welcome!"
    values = {key1: value1}
    
    result = formatter.format(template, values)
    
    assert f"{{{key1}}}" not in result
    assert value1 in result


@given(st.dictionaries(
    keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10),
    values=st.text(min_size=1, max_size=20),
    min_size=1,
    max_size=5,
))
@settings(max_examples=100)
def test_message_formatter_all_placeholders_replaced(values: dict[str, str]):
    """
    **Feature: generics-100-percent-fixes, Property 3: MessageFormatter Placeholder Substitution**
    **Validates: Requirements 2.2**
    
    All placeholders should be replaced.
    """
    formatter = DictMessageFormatter()
    
    # Build template with all keys as placeholders
    template_parts = [f"{{{k}}}" for k in values.keys()]
    template = " ".join(template_parts)
    
    result = formatter.format(template, values)
    
    # No placeholders should remain
    for key in values.keys():
        assert f"{{{key}}}" not in result
        assert values[key] in result


# =============================================================================
# Property 4: PluralRules Selection
# =============================================================================


@given(st.integers(min_value=0, max_value=1000))
@settings(max_examples=100)
def test_english_plural_rules_selection(count: int):
    """
    **Feature: generics-100-percent-fixes, Property 4: PluralRules Selection**
    **Validates: Requirements 2.4**
    
    For any count, select should return a value from the dict based on rules.
    """
    rules = EnglishPluralRules[str]()
    forms = {"one": "item", "other": "items"}
    
    result = rules.select(count, forms)
    
    if count == 1:
        assert result == "item"
    else:
        assert result == "items"


@given(st.integers(min_value=0, max_value=1000))
@settings(max_examples=100)
def test_portuguese_plural_rules_selection(count: int):
    """
    **Feature: generics-100-percent-fixes, Property 4: PluralRules Selection**
    **Validates: Requirements 2.4**
    
    Portuguese uses one for 0 and 1.
    """
    rules = PortuguesePluralRules[str]()
    forms = {"one": "item", "other": "itens"}
    
    result = rules.select(count, forms)
    
    if count in (0, 1):
        assert result == "item"
    else:
        assert result == "itens"


@given(st.integers(min_value=0, max_value=1000))
@settings(max_examples=100)
def test_russian_plural_rules_selection(count: int):
    """
    **Feature: generics-100-percent-fixes, Property 4: PluralRules Selection**
    **Validates: Requirements 2.4**
    
    Russian has complex plural rules.
    """
    rules = RussianPluralRules[str]()
    forms = {"one": "яблоко", "few": "яблока", "many": "яблок", "other": "яблок"}
    
    result = rules.select(count, forms)
    
    # Result should always be one of the forms
    assert result in forms.values()


# =============================================================================
# Property 5: TranslationCatalog Lookup
# =============================================================================


@given(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20),
    st.text(min_size=1, max_size=100),
    locale_strategy,
)
@settings(max_examples=100)
def test_translation_catalog_lookup(key: str, value: str, locale: Locale):
    """
    **Feature: generics-100-percent-fixes, Property 5: TranslationCatalog Lookup**
    **Validates: Requirements 2.5**
    
    For any registered key and locale, get should return the registered translation.
    """
    catalog = TranslationCatalog[str]()
    catalog.register(key, locale, value)
    
    result = catalog.get(key, locale)
    
    assert result == value


@given(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20),
    st.text(min_size=1, max_size=100),
    st.text(min_size=1, max_size=100),
)
@settings(max_examples=100)
def test_translation_catalog_get_or_default(key: str, value: str, default: str):
    """
    **Feature: generics-100-percent-fixes, Property 5: TranslationCatalog Lookup**
    **Validates: Requirements 2.5**
    
    get_or_default returns default when key not found.
    """
    catalog = TranslationCatalog[str]()
    
    # Key not registered
    result = catalog.get_or_default(key, EN_US, default)
    assert result == default
    
    # Register and try again
    catalog.register(key, EN_US, value)
    result = catalog.get_or_default(key, EN_US, default)
    assert result == value


# =============================================================================
# Property 7: DependencyResolutionError Contains Info
# =============================================================================


@given(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20),
)
@settings(max_examples=100)
def test_dependency_resolution_error_contains_info(param_name: str):
    """
    **Feature: generics-100-percent-fixes, Property 7: DependencyResolutionError Contains Info**
    **Validates: Requirements 4.1, 4.4**
    
    For any unresolvable dependency, the error should contain service_type,
    param_name, and expected_type.
    """
    @dataclass
    class MyService:
        pass
    
    @dataclass
    class MyDependency:
        pass
    
    error = DependencyResolutionError(
        service_type=MyService,
        param_name=param_name,
        expected_type=MyDependency,
    )
    
    assert error.service_type == MyService
    assert error.param_name == param_name
    assert error.expected_type == MyDependency
    assert param_name in str(error)
    assert "MyService" in str(error)
    assert "MyDependency" in str(error)


# =============================================================================
# Property 8: CircularDependencyError Contains Chain
# =============================================================================


def test_circular_dependency_error_contains_chain():
    """
    **Feature: generics-100-percent-fixes, Property 8: CircularDependencyError Contains Chain**
    **Validates: Requirements 4.2**
    
    For any circular dependency, the error should contain the complete chain.
    """
    class A:
        pass
    
    class B:
        pass
    
    class C:
        pass
    
    chain = [A, B, C, A]
    error = CircularDependencyError(chain)
    
    assert error.chain == chain
    assert "A" in str(error)
    assert "B" in str(error)
    assert "C" in str(error)
    assert "->" in str(error)


def test_circular_dependency_detection():
    """
    **Feature: generics-100-percent-fixes, Property 8: CircularDependencyError Contains Chain**
    **Validates: Requirements 4.2**
    
    Container should detect circular dependencies.
    """
    # Use a simpler approach - register with factories that create circular deps
    class ServiceA:
        def __init__(self) -> None:
            pass
    
    class ServiceB:
        def __init__(self) -> None:
            pass
    
    container = Container()
    
    # Create factories that will cause circular resolution
    def create_a() -> ServiceA:
        container.resolve(ServiceB)  # This will trigger circular check
        return ServiceA()
    
    def create_b() -> ServiceB:
        container.resolve(ServiceA)  # This will trigger circular check
        return ServiceB()
    
    container.register(ServiceA, create_a)
    container.register(ServiceB, create_b)
    
    with pytest.raises(CircularDependencyError) as exc_info:
        container.resolve(ServiceA)
    
    assert len(exc_info.value.chain) >= 2


# =============================================================================
# Property 9: Optional Dependency Handling
# =============================================================================


def test_optional_dependency_handling():
    """
    **Feature: generics-100-percent-fixes, Property 9: Optional Dependency Handling**
    **Validates: Requirements 4.3**
    
    For any service with Optional[T] dependency where T is not registered,
    resolution should succeed with None.
    """
    class OptionalDep:
        pass
    
    class ServiceWithOptional:
        def __init__(self, dep: Optional[OptionalDep] = None) -> None:
            self.dep = dep
    
    container = Container()
    container.register(ServiceWithOptional)
    # Note: OptionalDep is NOT registered
    
    service = container.resolve(ServiceWithOptional)
    
    assert service is not None
    assert service.dep is None


def test_optional_dependency_with_union_syntax():
    """
    **Feature: generics-100-percent-fixes, Property 9: Optional Dependency Handling**
    **Validates: Requirements 4.3**
    
    Test with T | None syntax.
    """
    class OptionalDep:
        pass
    
    class ServiceWithUnion:
        def __init__(self, dep: OptionalDep | None = None) -> None:
            self.dep = dep
    
    container = Container()
    container.register(ServiceWithUnion)
    
    service = container.resolve(ServiceWithUnion)
    
    assert service is not None
    assert service.dep is None


def test_required_dependency_raises_error():
    """
    **Feature: generics-100-percent-fixes, Property 9: Optional Dependency Handling**
    **Validates: Requirements 4.1**
    
    Required dependencies should raise error when not registered.
    """
    class RequiredDep:
        pass
    
    class ServiceWithRequired:
        def __init__(self, dep: RequiredDep) -> None:
            self.dep = dep
    
    container = Container()
    container.register(ServiceWithRequired)
    # Note: RequiredDep is NOT registered
    
    with pytest.raises(DependencyResolutionError) as exc_info:
        container.resolve(ServiceWithRequired)
    
    assert exc_info.value.param_name == "dep"
    assert exc_info.value.expected_type == RequiredDep


# =============================================================================
# Additional Container Tests
# =============================================================================


def test_container_singleton_lifetime():
    """Test singleton returns same instance."""
    class SingletonService:
        pass
    
    container = Container()
    container.register_singleton(SingletonService)
    
    instance1 = container.resolve(SingletonService)
    instance2 = container.resolve(SingletonService)
    
    assert instance1 is instance2


def test_container_transient_lifetime():
    """Test transient returns new instance each time."""
    class TransientService:
        pass
    
    container = Container()
    container.register(TransientService, lifetime=Lifetime.TRANSIENT)
    
    instance1 = container.resolve(TransientService)
    instance2 = container.resolve(TransientService)
    
    assert instance1 is not instance2


def test_container_auto_wiring():
    """Test auto-wiring resolves dependencies."""
    class Dependency:
        pass
    
    class ServiceWithDep:
        def __init__(self, dep: Dependency) -> None:
            self.dep = dep
    
    container = Container()
    container.register(Dependency)
    container.register(ServiceWithDep)
    
    service = container.resolve(ServiceWithDep)
    
    assert service.dep is not None
    assert isinstance(service.dep, Dependency)


def test_service_not_registered_error():
    """Test error when service not registered."""
    class NotRegistered:
        pass
    
    container = Container()
    
    with pytest.raises(ServiceNotRegisteredError) as exc_info:
        container.resolve(NotRegistered)
    
    assert exc_info.value.service_type == NotRegistered


def test_invalid_factory_error():
    """Test error for invalid factory."""
    container = Container()
    
    with pytest.raises(InvalidFactoryError):
        container.register(str, "not_callable")  # type: ignore
