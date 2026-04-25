import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/dns_target.dart';
import '../providers/monitor_provider.dart';
import '../widgets/glass_card.dart';
import '../widgets/latency_chart.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final TextEditingController _hostController = TextEditingController();
  int _currentTab = 0;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final provider = context.read<MonitorProvider>();
    _hostController.text = provider.singleHost;
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<MonitorProvider>();

    final pages = [
      _buildDashboard(provider),
      _buildDnsMonitor(provider),
      _buildHistory(provider),
      _buildSettings(provider),
    ];

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('Ping Watcher Android'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            onPressed: provider.toggleTheme,
            icon: Icon(provider.darkMode ? Icons.light_mode : Icons.dark_mode),
          ),
        ],
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF0D1117), Color(0xFF131C2B), Color(0xFF161B22)],
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: pages[_currentTab],
          ),
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentTab,
        onDestinationSelected: (index) => setState(() => _currentTab = index),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.speed), label: 'Dashboard'),
          NavigationDestination(icon: Icon(Icons.dns), label: 'DNS'),
          NavigationDestination(icon: Icon(Icons.history), label: 'History'),
          NavigationDestination(icon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
    );
  }

  Widget _buildDashboard(MonitorProvider provider) {
    final latest = provider.singleSamples.isNotEmpty ? provider.singleSamples.last : null;

    return ListView(
      children: [
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Single Target Monitor', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _hostController,
                      decoration: const InputDecoration(
                        labelText: 'Host',
                        hintText: '8.8.8.8 or google.com',
                      ),
                      onSubmitted: (value) => provider.updateSingleHost(value),
                    ),
                  ),
                  const SizedBox(width: 10),
                  ElevatedButton(
                    onPressed: () {
                      provider.updateSingleHost(_hostController.text.trim());
                      provider.startSingleMonitor();
                    },
                    child: const Text('Start'),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton(
                    onPressed: provider.stopSingleMonitor,
                    child: const Text('Stop'),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                latest == null
                    ? 'No sample yet'
                    : latest.success
                        ? 'Online · ${latest.latencyMs!.toStringAsFixed(1)} ms'
                        : 'Offline',
                style: TextStyle(
                  color: latest == null
                      ? Colors.white70
                      : latest.success
                          ? const Color(0xFF3FB950)
                          : const Color(0xFFF85149),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SizedBox(height: 250, child: GlassCard(child: LatencyChart(samples: provider.singleSamples))),
      ],
    );
  }

  Widget _buildDnsMonitor(MonitorProvider provider) {
    return Column(
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            ElevatedButton(onPressed: provider.startSelectedDnsBatch, child: const Text('Start Selected')),
            OutlinedButton(onPressed: provider.stopSelectedDnsBatch, child: const Text('Stop Selected')),
            ElevatedButton(onPressed: provider.startAllDnsBatch, child: const Text('Start All')),
            OutlinedButton(onPressed: provider.stopAllDnsBatch, child: const Text('Stop All')),
          ],
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView.builder(
            itemCount: defaultDnsTargets.length,
            itemBuilder: (context, index) {
              final dns = defaultDnsTargets[index];
              final selected = provider.selectedDns.contains(dns.address);
              final latest = provider.dnsLatest[dns.address];
              final running = provider.isDnsRunning(dns.address);

              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: GlassCard(
                  child: Row(
                    children: [
                      Checkbox(
                        value: selected,
                        onChanged: (_) => provider.toggleDnsSelection(dns.address),
                      ),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(dns.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                            Text('${dns.address} • ${dns.group}'),
                          ],
                        ),
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(running ? 'Running' : 'Stopped'),
                          Text(
                            latest == null
                                ? 'No data'
                                : latest.success
                                    ? '${latest.latencyMs!.toStringAsFixed(1)} ms'
                                    : 'Offline',
                            style: TextStyle(
                              color: latest == null
                                  ? Colors.white70
                                  : latest.success
                                      ? const Color(0xFF3FB950)
                                      : const Color(0xFFF85149),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildHistory(MonitorProvider provider) {
    final items = provider.history.reversed.take(200).toList();
    final formatter = DateFormat('HH:mm:ss');

    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (context, index) {
        final sample = items[index];
        return ListTile(
          leading: Icon(sample.success ? Icons.check_circle : Icons.error,
              color: sample.success ? const Color(0xFF3FB950) : const Color(0xFFF85149)),
          title: Text(sample.host),
          subtitle: Text(formatter.format(sample.time)),
          trailing: Text(sample.latencyMs == null ? '—' : '${sample.latencyMs!.toStringAsFixed(1)} ms'),
        );
      },
    );
  }

  Widget _buildSettings(MonitorProvider provider) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Settings', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          Text('Interval: ${provider.intervalMs} ms'),
          Slider(
            value: provider.intervalMs.toDouble(),
            min: 300,
            max: 5000,
            divisions: 47,
            label: '${provider.intervalMs} ms',
            onChanged: (value) {
              provider.intervalMs = value.toInt();
              provider.saveSettings();
              provider.notifyListeners();
            },
          ),
          SwitchListTile(
            value: provider.darkMode,
            onChanged: (_) => provider.toggleTheme(),
            title: const Text('Dark mode'),
          ),
        ],
      ),
    );
  }
}
