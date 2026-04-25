import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/dns_target.dart';
import '../models/ping_sample.dart';
import '../services/latency_service.dart';

class MonitorProvider extends ChangeNotifier {
  final LatencyService _latencyService = LatencyService();

  String singleHost = '8.8.8.8';
  bool isMonitoringSingle = false;
  bool darkMode = true;
  int intervalMs = 1000;

  Timer? _singleTimer;
  final List<PingSample> singleSamples = [];
  final List<PingSample> history = [];

  final Set<String> selectedDns = {};
  final Map<String, PingSample> dnsLatest = {};
  final Map<String, Timer> _dnsTimers = {};

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    darkMode = prefs.getBool('darkMode') ?? true;
    intervalMs = prefs.getInt('intervalMs') ?? 1000;
    singleHost = prefs.getString('singleHost') ?? '8.8.8.8';
    notifyListeners();
  }

  Future<void> saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('darkMode', darkMode);
    await prefs.setInt('intervalMs', intervalMs);
    await prefs.setString('singleHost', singleHost);
  }

  void toggleTheme() {
    darkMode = !darkMode;
    saveSettings();
    notifyListeners();
  }

  void updateSingleHost(String host) {
    singleHost = host;
    saveSettings();
    notifyListeners();
  }

  Future<void> startSingleMonitor() async {
    if (isMonitoringSingle) return;
    isMonitoringSingle = true;
    notifyListeners();

    await _runSingleCheck();
    _singleTimer = Timer.periodic(Duration(milliseconds: intervalMs), (_) async {
      await _runSingleCheck();
    });
  }

  void stopSingleMonitor() {
    _singleTimer?.cancel();
    _singleTimer = null;
    isMonitoringSingle = false;
    notifyListeners();
  }

  Future<void> _runSingleCheck() async {
    final sample = await _latencyService.checkHost(singleHost);
    singleSamples.add(sample);
    history.add(sample);

    if (singleSamples.length > 120) {
      singleSamples.removeAt(0);
    }
    if (history.length > 3000) {
      history.removeAt(0);
    }
    notifyListeners();
  }

  void toggleDnsSelection(String host) {
    if (selectedDns.contains(host)) {
      selectedDns.remove(host);
    } else {
      selectedDns.add(host);
    }
    notifyListeners();
  }

  void startSelectedDnsBatch() {
    for (final host in selectedDns) {
      _startDns(host);
    }
    notifyListeners();
  }

  void stopSelectedDnsBatch() {
    for (final host in selectedDns) {
      _stopDns(host);
    }
    notifyListeners();
  }

  void startAllDnsBatch() {
    for (final target in defaultDnsTargets) {
      _startDns(target.address);
    }
    notifyListeners();
  }

  void stopAllDnsBatch() {
    final keys = _dnsTimers.keys.toList();
    for (final host in keys) {
      _stopDns(host);
    }
    notifyListeners();
  }

  bool isDnsRunning(String host) => _dnsTimers.containsKey(host);

  void _startDns(String host) {
    if (_dnsTimers.containsKey(host)) return;

    _checkDnsHost(host);
    _dnsTimers[host] = Timer.periodic(Duration(milliseconds: intervalMs), (_) {
      _checkDnsHost(host);
    });
  }

  void _stopDns(String host) {
    _dnsTimers[host]?.cancel();
    _dnsTimers.remove(host);
  }

  Future<void> _checkDnsHost(String host) async {
    final sample = await _latencyService.checkHost(host);
    dnsLatest[host] = sample;
    history.add(sample);
    if (history.length > 3000) {
      history.removeAt(0);
    }
    notifyListeners();
  }

  @override
  void dispose() {
    _singleTimer?.cancel();
    for (final timer in _dnsTimers.values) {
      timer.cancel();
    }
    super.dispose();
  }
}
