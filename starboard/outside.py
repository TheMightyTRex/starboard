"""Addresses Starboard is told to call (DASH-279): an app's address in Manage apps, its test, and the servers that
history and listening progress are read from. Your own apps live on this computer and your home network, so those
addresses are fine; what is refused is what no media app uses and what an attacker would aim at: link-local
addresses (169.254.x.x, fe80::), which include the cloud metadata services, multicast, broadcast and "any" addresses,
and the metadata services' names. Redirects are checked the same way (services._KeepKeysHome), and an app's request
that carries its key is never followed to another server.
"""
import ipaddress
import socket
import urllib.parse

METADATA_NAMES = {"metadata", "metadata.google.internal", "metadata.goog", "instance-data", "instance-data.ec2.internal"}
TIMEOUT = 2


def bad_address(ip):
    """Why an IP address is refused, or "" when it is fine."""
    try:
        a = ipaddress.ip_address(ip.split("%", 1)[0])
    except ValueError:
        return "it is not an address"
    if isinstance(a, ipaddress.IPv6Address) and a.ipv4_mapped:
        a = a.ipv4_mapped
    if a.is_link_local:
        return "it is a link-local address, which no media app uses (cloud servers keep their secrets there)"
    if a.is_multicast or a.is_unspecified or (isinstance(a, ipaddress.IPv4Address) and a == ipaddress.IPv4Address("255.255.255.255")):
        return "it is not one computer's address"
    if isinstance(a, ipaddress.IPv6Address) and a in ipaddress.ip_network("fd00:ec2::/32"):
        return "it is a cloud metadata address"
    return ""


def check_url(url, resolve=None):
    """Raises ValueError with the reason when Starboard must not call this address. A name that does not resolve
    here is let through: Starboard cannot reach it either, and the app's check says so."""
    parts = urllib.parse.urlsplit(str(url or ""))
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("The address must start with http:// or https://")
    host = parts.hostname.rstrip(".").lower()
    if host in METADATA_NAMES:
        raise ValueError(f"Starboard does not call {host}: it is a cloud metadata service")
    try:
        ipaddress.ip_address(host.split("%", 1)[0])
        addresses = [host]
    except ValueError:
        try:
            infos = (resolve or socket.getaddrinfo)(host, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)
            addresses = sorted({i[4][0] for i in infos})
        except (OSError, UnicodeError):
            return
    for ip in addresses:
        why = bad_address(ip)
        if why:
            raise ValueError(f"Starboard does not call {host}: {why}")
