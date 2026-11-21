import 'package:material_ui/material_ui.dart';

import '../../../shared/widgets/dashboard_menu.dart';

class HodDashboardScreen extends StatelessWidget {
  const HodDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) => const DashboardMenu(
    title: 'HOD Dashboard',
    destinations: [
      DashboardDestination(
        title: 'Faculty Timetable',
        subtitle: 'View your teaching schedule',
        route: '/faculty/timetable',
        icon: Icons.calendar_month_outlined,
      ),
      DashboardDestination(
        title: 'Room Availability Finder',
        subtitle: 'Find available rooms',
        route: '/rooms/availability',
        icon: Icons.meeting_room_outlined,
      ),
      DashboardDestination(
        title: 'Energy Dashboard',
        subtitle: 'Read energy and utilization reports',
        route: '/energy',
        icon: Icons.bolt_outlined,
      ),
      DashboardDestination(
        title: 'Campus Map',
        subtitle: 'View room layouts and occupancy',
        route: '/campus-map',
        icon: Icons.map_outlined,
      ),
      DashboardDestination(
        title: 'Route Navigator',
        subtitle: 'Find a route between rooms',
        route: '/route-navigator',
        icon: Icons.alt_route,
      ),
    ],
  );
}
