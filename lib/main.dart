import 'package:dio/dio.dart';
import 'package:material_ui/material_ui.dart';

void main() {
  runApp(const PblApp());
}

class PblApp extends StatelessWidget {
  const PblApp({super.key, this.healthCheck});

  final Future<String> Function()? healthCheck;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PBL Campus',
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
      home: HealthScreen(healthCheck: healthCheck),
    );
  }
}

class HealthScreen extends StatefulWidget {
  const HealthScreen({super.key, this.healthCheck});

  final Future<String> Function()? healthCheck;

  @override
  State<HealthScreen> createState() => _HealthScreenState();
}

class _HealthScreenState extends State<HealthScreen> {
  late final Future<String> _health = _loadHealth();

  Future<String> _loadHealth() async {
    if (widget.healthCheck case final healthCheck?) {
      return healthCheck();
    }
    final dio = Dio(
      BaseOptions(
        baseUrl: const String.fromEnvironment(
          'PBL_API_URL',
          defaultValue: 'http://10.0.2.2:8000',
        ),
      ),
    );
    final response = await dio.get<Map<String, dynamic>>('/health');
    return response.data?['status'] as String? ?? 'unknown';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('PBL Campus')),
      body: Center(
        child: FutureBuilder<String>(
          future: _health,
          builder: (context, snapshot) {
            final message = switch (snapshot.connectionState) {
              ConnectionState.waiting => 'Checking backend connection…',
              _ when snapshot.hasError => 'Backend unavailable',
              _ => 'Backend status: ${snapshot.data}',
            };
            return Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.account_balance, size: 48),
                const SizedBox(height: 12),
                Text(message, textAlign: TextAlign.center),
              ],
            );
          },
        ),
      ),
    );
  }
}
