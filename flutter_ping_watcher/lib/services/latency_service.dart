import 'dart:io';

import '../models/ping_sample.dart';

class LatencyService {
  Future<PingSample> checkHost(String host) async {
    final started = DateTime.now();
    try {
      final socket = await Socket.connect(host, 53, timeout: const Duration(seconds: 2));
      final ended = DateTime.now();
      await socket.close();
      return PingSample(
        host: host,
        time: ended,
        latencyMs: ended.difference(started).inMicroseconds / 1000.0,
        success: true,
      );
    } catch (_) {
      return PingSample(
        host: host,
        time: DateTime.now(),
        latencyMs: null,
        success: false,
      );
    }
  }
}
