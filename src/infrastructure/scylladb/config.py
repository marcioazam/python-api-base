"""ScyllaDB configuration.

**Feature: observability-infrastructure**
**Requirement: R4 - Generic ScyllaDB Repository**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScyllaDBConfig:
    """Configuration for ScyllaDB client.

    Attributes:
        hosts: List of contact points
        port: CQL native port
        keyspace: Default keyspace
        username: Authentication username
        password: Authentication password
        protocol_version: CQL protocol version
        connect_timeout: Connection timeout in seconds
        request_timeout: Request timeout in seconds
        consistency_level: Default consistency level
        local_dc: Local datacenter for DC-aware routing
        ssl_enabled: Whether to use SSL
        ssl_certfile: Path to SSL certificate
        ssl_keyfile: Path to SSL key
    """

    hosts: list[str] = field(default_factory=lambda: ["localhost"])
    port: int = 9042
    keyspace: str = "python_api_base"
    username: str | None = None
    password: str | None = None
    protocol_version: int = 4
    connect_timeout: int = 10
    request_timeout: int = 30
    consistency_level: str = "LOCAL_QUORUM"
    local_dc: str | None = None
    ssl_enabled: bool = False
    ssl_certfile: str | None = None
    ssl_keyfile: str | None = None

    def to_cluster_kwargs(self) -> dict[str, Any]:
        """Convert to cassandra-driver Cluster kwargs.

        Returns:
            Cluster configuration dict
        """
        from cassandra.policies import (
            DCAwareRoundRobinPolicy,
            TokenAwarePolicy,
        )

        kwargs: dict[str, Any] = {
            "contact_points": self.hosts,
            "port": self.port,
            "protocol_version": self.protocol_version,
            "connect_timeout": self.connect_timeout,
        }

        # Auth
        if self.username and self.password:
            from cassandra.auth import PlainTextAuthProvider

            kwargs["auth_provider"] = PlainTextAuthProvider(
                username=self.username,
                password=self.password,
            )

        # Load balancing
        if self.local_dc:
            lb_policy = TokenAwarePolicy(
                DCAwareRoundRobinPolicy(local_dc=self.local_dc)
            )
            kwargs["load_balancing_policy"] = lb_policy

        # SSL
        if self.ssl_enabled:
            import ssl

            ssl_context = ssl.create_default_context()
            if self.ssl_certfile:
                ssl_context.load_cert_chain(
                    certfile=self.ssl_certfile,
                    keyfile=self.ssl_keyfile,
                )
            kwargs["ssl_context"] = ssl_context

        return kwargs

    def get_consistency_level(self) -> Any:
        """Get consistency level object.

        Returns:
            ConsistencyLevel enum value
        """
        from cassandra import ConsistencyLevel

        return getattr(ConsistencyLevel, self.consistency_level)
