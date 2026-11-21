import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/authentication/authentication_screen.dart';
import 'dashboard_components.dart';

class DashboardDestination {
  const DashboardDestination({
    required this.title,
    required this.route,
    required this.icon,
    this.subtitle,
  });

  final String title;
  final String route;
  final IconData icon;
  final String? subtitle;
}

class DashboardMenu extends ConsumerWidget {
  const DashboardMenu({
    super.key,
    required this.title,
    required this.destinations,
    this.showStudentMetadata = false,
  });

  final String title;
  final List<DashboardDestination> destinations;
  final bool showStudentMetadata;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).value;
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: [
          PopupMenuButton<String>(
            tooltip: 'Account menu',
            onSelected: (value) {
              if (value == 'logout') {
                ref.read(authProvider.notifier).logout();
              }
            },
            itemBuilder: (context) => const [
              PopupMenuItem(
                value: 'logout',
                child: Row(
                  children: [
                    Icon(Icons.logout),
                    SizedBox(width: 12),
                    Text('Logout'),
                  ],
                ),
              ),
            ],
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: CircleAvatar(
                radius: 17,
                backgroundColor: const Color(0xFF14B8A6),
                child: Text(
                  _initials(user?.fullName ?? ''),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
      body: ListView(
        children: [
          DashboardHeader(
            name: user?.fullName ?? '-',
            role: user?.role ?? '-',
            category: user?.category ?? '-',
            showStudentMetadata: showStudentMetadata,
          ),
          GridView.builder(
            padding: const EdgeInsets.all(16),
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              mainAxisExtent: 116,
            ),
            itemCount: destinations.length,
            itemBuilder: (context, index) {
              final destination = destinations[index];
              return FeatureTile(
                icon: destination.icon,
                label: destination.title,
                subtitle: destination.subtitle,
                onTap: () => context.go(destination.route),
              );
            },
          ),
        ],
      ),
    );
  }

  String _initials(String name) {
    final parts = name
        .trim()
        .split(RegExp(r'\s+'))
        .where((part) => part.isNotEmpty);
    final values = parts.take(2).map((part) => part[0].toUpperCase()).join();
    return values.isEmpty ? '?' : values;
  }
}
