"""HTTP/2 Protocol Constants per RFC 7540.

This module defines constants for HTTP/2 protocol limits as specified
in RFC 7540 (Hypertext Transfer Protocol Version 2).

**Feature: shared-modules-phase3-fixes, Task 5.7**
**Validates: Requirements 8.1, 8.2, 8.3**
"""

# RFC 7540 Section 6.5.2 - SETTINGS_MAX_CONCURRENT_STREAMS
# The maximum number of concurrent streams that the sender will allow.
# This limit is directional: it applies to the number of streams that
# the sender permits the receiver to create.
MAX_CONCURRENT_STREAMS_LIMIT = 2147483647

# RFC 7540 Section 6.9.1 - Initial Window Size
# The initial window size for flow control. The maximum value is 2^31-1.
MAX_WINDOW_SIZE = 2147483647

# RFC 7540 Section 4.2 - Frame Size
# The size of a frame payload is limited by the maximum size that a
# receiver advertises in the SETTINGS_MAX_FRAME_SIZE setting.
MIN_FRAME_SIZE = 16384  # 2^14 - minimum allowed value
MAX_FRAME_SIZE = 16777215  # 2^24-1 - maximum allowed value

# RFC 7540 Section 6.5.2 - SETTINGS_MAX_HEADER_LIST_SIZE
# This advisory setting informs a peer of the maximum size of header
# list that the sender is prepared to accept, in octets.
DEFAULT_MAX_HEADER_LIST_SIZE = 8192

# RFC 7540 Section 6.9.2 - Initial Flow-Control Window Size
# The initial value for the flow-control window is 65,535 octets.
DEFAULT_INITIAL_WINDOW_SIZE = 65535

# RFC 7540 Section 6.5.2 - Default max concurrent streams
DEFAULT_MAX_CONCURRENT_STREAMS = 100
