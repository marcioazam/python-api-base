"""Fingerprint enums.

**Feature: file-size-compliance-phase2, Task 2.6**
**Validates: Requirements 1.6, 5.1, 5.2, 5.3**
"""

from enum import Enum


class FingerprintComponent(Enum):
    """Components used in fingerprint generation."""

    IP_ADDRESS = "ip_address"
    USER_AGENT = "user_agent"
    ACCEPT_LANGUAGE = "accept_language"
    ACCEPT_ENCODING = "accept_encoding"
    ACCEPT = "accept"
    CONNECTION = "connection"
    CACHE_CONTROL = "cache_control"
    DNT = "dnt"
    UPGRADE_INSECURE = "upgrade_insecure"
    SEC_FETCH_SITE = "sec_fetch_site"
    SEC_FETCH_MODE = "sec_fetch_mode"
    SEC_FETCH_DEST = "sec_fetch_dest"
    SEC_CH_UA = "sec_ch_ua"
    SEC_CH_UA_MOBILE = "sec_ch_ua_mobile"
    SEC_CH_UA_PLATFORM = "sec_ch_ua_platform"
    TIMEZONE = "timezone"
    SCREEN_RESOLUTION = "screen_resolution"
    COLOR_DEPTH = "color_depth"
    PLUGINS = "plugins"
    FONTS = "fonts"
    CANVAS = "canvas"
    WEBGL = "webgl"
    AUDIO = "audio"


class SuspicionLevel(Enum):
    """Level of suspicion for a fingerprint."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
