"""Cloud provider enumerations."""

from enum import Enum


class CloudProvider(str, Enum):
    """Known cloud providers."""

    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    DIGITALOCEAN = "digitalocean"
    LINODE = "linode"
    VULTR = "vultr"
    OVH = "ovh"
    HETZNER = "hetzner"
    ORACLE = "oracle"
    IBM = "ibm"
    ALIBABA = "alibaba"
    CLOUDFLARE = "cloudflare"
    UNKNOWN = "unknown"
