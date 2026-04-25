class DnsTarget {
  final String name;
  final String address;
  final String group;

  const DnsTarget({
    required this.name,
    required this.address,
    required this.group,
  });
}

const List<DnsTarget> defaultDnsTargets = [
  DnsTarget(name: 'Google DNS 1', address: '8.8.8.8', group: 'external'),
  DnsTarget(name: 'Google DNS 2', address: '8.8.4.4', group: 'external'),
  DnsTarget(name: 'Cloudflare DNS 1', address: '1.1.1.1', group: 'external'),
  DnsTarget(name: 'Cloudflare DNS 2', address: '1.0.0.1', group: 'external'),
  DnsTarget(name: 'OpenDNS 1', address: '208.67.222.222', group: 'external'),
  DnsTarget(name: 'Shecan 1', address: '178.22.122.100', group: 'internal'),
  DnsTarget(name: 'Shecan 2', address: '185.51.200.2', group: 'internal'),
  DnsTarget(name: 'Radar Game', address: '10.202.10.10', group: 'internal'),
  DnsTarget(name: 'Local Gateway', address: '192.168.1.1', group: 'internal'),
];
