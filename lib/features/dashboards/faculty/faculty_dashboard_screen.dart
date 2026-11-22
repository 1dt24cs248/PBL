import 'package:material_ui/material_ui.dart';

import '../../../shared/widgets/dashboard_menu.dart';

class FacultyDashboardScreen extends StatelessWidget {
  const FacultyDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) => const DashboardMenu(
    title: 'Faculty Dashboard',
    destinations: [
      DashboardDestination(
        title: 'Time Table',
        subtitle: 'View your teaching schedule',
        route: '/faculty/timetable',
        icon: Icons.calendar_month_outlined,
      ),
      DashboardDestination(
        title: 'Room Finder',
        route: '/rooms/availability',
        icon: Icons.meeting_room_outlined,
      ),
      DashboardDestination(
        title: 'Campus Map',
        route: '/campus-map',
        icon: Icons.map_outlined,
      ),
      DashboardDestination(
        title: 'Route Navigator',
        route: '/route-navigator',
        icon: Icons.alt_route,
      ),
      DashboardDestination(
        title: 'Notifications',
        route: '/notifications',
        icon: Icons.notifications_outlined,
      ),
    ],
  );
}
