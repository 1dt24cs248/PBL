import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../authentication/authentication_screen.dart';
import '../../../shared/widgets/dashboard_menu.dart';

class ManagementDashboardScreen extends ConsumerWidget {
  const ManagementDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isAdmin = ref.watch(authProvider).value?.role == 'admin';
    return DashboardMenu(
      title: 'Management Dashboard',
      destinations: [
        const DashboardDestination(
        title: 'Room Availability Finder',
        subtitle: 'Find available rooms',
        route: '/rooms/availability',
        icon: Icons.meeting_room_outlined,
      ),
        if (isAdmin)
          const DashboardDestination(
            title: 'Energy & Optimization',
            subtitle: 'Review energy use and proposals',
            route: '/energy',
            icon: Icons.bolt_outlined,
          ),
      ],
    );
  }
}
