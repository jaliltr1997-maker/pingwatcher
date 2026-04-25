class PingSample {
  final String host;
  final DateTime time;
  final double? latencyMs;
  final bool success;

  const PingSample({
    required this.host,
    required this.time,
    required this.latencyMs,
    required this.success,
  });
}
