import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/authentication/authentication_screen.dart';

class DashboardDestination {
  const DashboardDestination({
    required this.title,
    required this.subtitle,
    required this.route,
    required this.icon,
  });

  final String title;
  final String subtitle;
  final String route;
  final IconData icon;
}

class DashboardMenu extends ConsumerWidget {
  const DashboardMenu({
    super.key,
    required this.title,
    required this.destinations,
  });

  final String title;
  final List<DashboardDestination> destinations;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: [
          IconButton(
            tooltip: 'Logout',
            onPressed: () => ref.read(authProvider.notifier).logout(),
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          for (final destination in destinations)
            Card(
              child: ListTile(
                leading: Icon(destination.icon),
                title: Text(destination.title),
                subtitle: Text(destination.subtitle),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.go(destination.route),
              ),
            ),
        ],
      ),
    );
  }
}
