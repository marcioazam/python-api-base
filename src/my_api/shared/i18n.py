"""Internationalization (i18n) support.

Provides translation services and locale handling.

**Feature: api-architecture-analysis, Property 5: i18n support**
**Validates: Requirements 4.4**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import re


class Locale(str, Enum):
    """Supported locales."""

    EN_US = "en-US"
    EN_GB = "en-GB"
    PT_BR = "pt-BR"
    ES_ES = "es-ES"
    FR_FR = "fr-FR"
    DE_DE = "de-DE"
    IT_IT = "it-IT"
    JA_JP = "ja-JP"
    ZH_CN = "zh-CN"
    KO_KR = "ko-KR"

    @property
    def language(self) -> str:
        """Get the language code."""
        return self.value.split("-")[0]

    @property
    def region(self) -> str:
        """Get the region code."""
        return self.value.split("-")[1]


@dataclass(slots=True)
class TranslationEntry:
    """A single translation entry."""

    key: str
    value: str
    locale: Locale
    context: str | None = None
    plural_forms: dict[str, str] = field(default_factory=dict)

    def get_plural(self, count: int) -> str:
        """Get the appropriate plural form."""
        if count == 1:
            return self.value
        return self.plural_forms.get("other", self.value)


class TranslationCatalog:
    """Catalog of translations for a locale."""

    def __init__(self, locale: Locale):
        self.locale = locale
        self._entries: dict[str, TranslationEntry] = {}

    def add(
        self,
        key: str,
        value: str,
        context: str | None = None,
        plural_forms: dict[str, str] | None = None,
    ) -> None:
        """Add a translation entry."""
        self._entries[key] = TranslationEntry(
            key=key,
            value=value,
            locale=self.locale,
            context=context,
            plural_forms=plural_forms or {},
        )

    def get(self, key: str) -> TranslationEntry | None:
        """Get a translation entry."""
        return self._entries.get(key)

    def has(self, key: str) -> bool:
        """Check if a translation exists."""
        return key in self._entries

    def keys(self) -> list[str]:
        """Get all translation keys."""
        return list(self._entries.keys())

    def __len__(self) -> int:
        return len(self._entries)


class TranslationService:
    """Service for managing translations."""

    def __init__(self, default_locale: Locale = Locale.EN_US):
        self.default_locale = default_locale
        self._catalogs: dict[Locale, TranslationCatalog] = {}
        self._fallback_chain: dict[Locale, list[Locale]] = {}

    def register_catalog(self, catalog: TranslationCatalog) -> None:
        """Register a translation catalog."""
        self._catalogs[catalog.locale] = catalog

    def set_fallback_chain(self, locale: Locale, fallbacks: list[Locale]) -> None:
        """Set fallback locales for a locale."""
        self._fallback_chain[locale] = fallbacks

    def get_catalog(self, locale: Locale) -> TranslationCatalog | None:
        """Get a translation catalog."""
        return self._catalogs.get(locale)

    def translate(
        self,
        key: str,
        locale: Locale | None = None,
        params: dict[str, Any] | None = None,
        count: int | None = None,
    ) -> str:
        """Translate a key to the specified locale."""
        target_locale = locale or self.default_locale
        locales_to_try = [target_locale] + self._fallback_chain.get(
            target_locale, [self.default_locale]
        )

        for loc in locales_to_try:
            catalog = self._catalogs.get(loc)
            if catalog:
                entry = catalog.get(key)
                if entry:
                    value = entry.get_plural(count) if count is not None else entry.value
                    return self._interpolate(value, params or {})

        return key

    def _interpolate(self, template: str, params: dict[str, Any]) -> str:
        """Interpolate parameters into a template."""
        result = template
        for param_key, param_value in params.items():
            result = result.replace(f"{{{param_key}}}", str(param_value))
        return result

    def t(
        self,
        key: str,
        locale: Locale | None = None,
        **kwargs: Any,
    ) -> str:
        """Shorthand for translate."""
        count = kwargs.pop("count", None)
        return self.translate(key, locale, kwargs, count)

    def list_locales(self) -> list[Locale]:
        """List all registered locales."""
        return list(self._catalogs.keys())

    def has_locale(self, locale: Locale) -> bool:
        """Check if a locale is registered."""
        return locale in self._catalogs


def parse_accept_language(header: str) -> list[tuple[Locale, float]]:
    """Parse Accept-Language header and return sorted locales with quality."""
    if not header:
        return []

    result: list[tuple[Locale, float]] = []
    pattern = re.compile(r"([a-zA-Z]{2}(?:-[a-zA-Z]{2})?)\s*(?:;\s*q=([0-9.]+))?")

    for match in pattern.finditer(header):
        lang = match.group(1)
        quality = float(match.group(2)) if match.group(2) else 1.0

        try:
            normalized = lang.replace("_", "-")
            if "-" not in normalized:
                normalized = f"{normalized}-{normalized.upper()}"
            locale = Locale(normalized)
            result.append((locale, quality))
        except ValueError:
            continue

    return sorted(result, key=lambda x: x[1], reverse=True)


def get_best_locale(
    accept_language: str,
    available_locales: list[Locale],
    default: Locale = Locale.EN_US,
) -> Locale:
    """Get the best matching locale from Accept-Language header."""
    parsed = parse_accept_language(accept_language)

    for locale, _ in parsed:
        if locale in available_locales:
            return locale
        for available in available_locales:
            if locale.language == available.language:
                return available

    return default


def create_translation_service() -> TranslationService:
    """Create a translation service with default catalogs."""
    service = TranslationService()

    en_catalog = TranslationCatalog(Locale.EN_US)
    en_catalog.add("error.not_found", "Resource not found")
    en_catalog.add("error.unauthorized", "Unauthorized access")
    en_catalog.add("error.validation", "Validation error: {field}")
    en_catalog.add(
        "items.count",
        "{count} item",
        plural_forms={"other": "{count} items"},
    )
    service.register_catalog(en_catalog)

    pt_catalog = TranslationCatalog(Locale.PT_BR)
    pt_catalog.add("error.not_found", "Recurso não encontrado")
    pt_catalog.add("error.unauthorized", "Acesso não autorizado")
    pt_catalog.add("error.validation", "Erro de validação: {field}")
    pt_catalog.add(
        "items.count",
        "{count} item",
        plural_forms={"other": "{count} itens"},
    )
    service.register_catalog(pt_catalog)

    service.set_fallback_chain(Locale.PT_BR, [Locale.EN_US])

    return service
