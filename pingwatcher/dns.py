from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DnsTarget:
    name: str
    address: str
    group: str  # external | internal


DEFAULT_DNS_TARGETS: list[DnsTarget] = [
    DnsTarget("Google DNS 1", "8.8.8.8", "external"),
    DnsTarget("Google DNS 2", "8.8.4.4", "external"),
    DnsTarget("Cloudflare DNS 1", "1.1.1.1", "external"),
    DnsTarget("Cloudflare DNS 2", "1.0.0.1", "external"),
    DnsTarget("Quad9", "9.9.9.9", "external"),
    DnsTarget("OpenDNS 1", "208.67.222.222", "external"),
    DnsTarget("OpenDNS 2", "208.67.220.220", "external"),
    DnsTarget("Shecan 1", "178.22.122.100", "internal"),
    DnsTarget("Shecan 2", "185.51.200.2", "internal"),
    DnsTarget("Radar Game", "10.202.10.10", "internal"),
    DnsTarget("Electro 1", "78.157.42.100", "internal"),
    DnsTarget("Electro 2", "78.157.42.101", "internal"),
    DnsTarget("Local Gateway", "192.168.1.1", "internal"),
]
