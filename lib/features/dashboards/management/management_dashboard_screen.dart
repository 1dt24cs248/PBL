import 'package:material_ui/material_ui.dart';

import '../../../shared/widgets/dashboard_menu.dart';

class ManagementDashboardScreen extends StatelessWidget {
  const ManagementDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) => const DashboardMenu(
    title: 'Management Dashboard',
    destinations: [
      DashboardDestination(
        title: 'Room Availability Finder',
        subtitle: 'Find available rooms',
        route: '/rooms/availability',
        icon: Icons.meeting_room_outlined,
      ),
    ],
  );
}
