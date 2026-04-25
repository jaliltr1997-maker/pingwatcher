import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../models/ping_sample.dart';

class LatencyChart extends StatelessWidget {
  final List<PingSample> samples;
  const LatencyChart({super.key, required this.samples});

  @override
  Widget build(BuildContext context) {
    final valid = samples.where((e) => e.latencyMs != null).toList();
    if (valid.length < 2) {
      return const Center(child: Text('Not enough data yet'));
    }

    final spots = <FlSpot>[];
    for (int i = 0; i < valid.length; i++) {
      spots.add(FlSpot(i.toDouble(), valid[i].latencyMs!));
    }

    final maxY = (valid.map((e) => e.latencyMs!).reduce((a, b) => a > b ? a : b) * 1.2).clamp(20, 2000).toDouble();

    return LineChart(
      LineChartData(
        minY: 0,
        maxY: maxY,
        gridData: FlGridData(show: true, drawVerticalLine: false),
        titlesData: const FlTitlesData(
          rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: const Color(0xFF58A6FF),
            barWidth: 3,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              gradient: LinearGradient(
                colors: [
                  const Color(0xFF58A6FF).withOpacity(0.4),
                  const Color(0xFF58A6FF).withOpacity(0.02),
                ],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
