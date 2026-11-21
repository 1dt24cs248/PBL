import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../authentication/authentication_screen.dart';

class StudentDashboardScreen extends ConsumerWidget {
  const StudentDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final user = auth.value;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Student Dashboard'),
        actions: [
          IconButton(
            tooltip: 'Logout',
            onPressed: () => ref.read(authProvider.notifier).logout(),
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: user == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user.fullName,
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text('Category: ${user.category}'),
                        Text('Role: ${user.role}'),
                        if (user.department.isNotEmpty)
                          Text('Department: ${user.department}'),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.today_outlined),
                    title: const Text("Today's timetable"),
                    subtitle: const Text('View student timetable'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.go('/student/timetable'),
                  ),
                ),
                const SizedBox(height: 8),
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.meeting_room_outlined),
                    title: const Text('Room Availability Finder'),
                    subtitle: const Text('Find available rooms'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.go('/rooms/availability'),
                  ),
                ),
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.map_outlined),
                    title: const Text('Campus Map'),
                    subtitle: const Text('View room layouts and occupancy'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.go('/campus-map'),
                  ),
                ),
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.alt_route),
                    title: const Text('Route Navigator'),
                    subtitle: const Text('Find a route between rooms'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.go('/route-navigator'),
                  ),
                ),
              ],
            ),
    );
  }
}
