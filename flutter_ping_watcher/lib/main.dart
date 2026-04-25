import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import 'providers/monitor_provider.dart';
import 'screens/home_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final provider = MonitorProvider();
  await provider.init();

  runApp(
    ChangeNotifierProvider.value(
      value: provider,
      child: const PingWatcherApp(),
    ),
  );
}

class PingWatcherApp extends StatelessWidget {
  const PingWatcherApp({super.key});

  @override
  Widget build(BuildContext context) {
    final monitor = context.watch<MonitorProvider>();
    return MaterialApp(
      title: 'Ping Watcher Android',
      debugShowCheckedModeBanner: false,
      themeMode: monitor.darkMode ? ThemeMode.dark : ThemeMode.light,
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        textTheme: GoogleFonts.vazirmatnTextTheme(ThemeData.dark().textTheme),
        useMaterial3: true,
      ),
      theme: ThemeData(
        brightness: Brightness.light,
        textTheme: GoogleFonts.vazirmatnTextTheme(ThemeData.light().textTheme),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
