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
        if (isAdmin)
          const DashboardDestination(
            title: 'Energy',
            route: '/energy',
            icon: Icons.bolt_outlined,
          ),
        if (isAdmin)
          const DashboardDestination(
            title: 'Optimizer',
            route: '/energy/optimizer',
            icon: Icons.tune_outlined,
          ),
        if (isAdmin)
          const DashboardDestination(
            title: 'Proposals',
            route: '/proposals',
            icon: Icons.fact_check_outlined,
          ),
        const DashboardDestination(
          title: 'Room Finder',
          route: '/rooms/availability',
          icon: Icons.meeting_room_outlined,
        ),
        const DashboardDestination(
          title: 'Campus Map',
          route: '/campus-map',
          icon: Icons.map_outlined,
        ),
        const DashboardDestination(
          title: 'Route Navigator',
          route: '/route-navigator',
          icon: Icons.alt_route,
        ),
      ],
    );
  }
}
