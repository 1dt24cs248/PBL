import 'package:material_ui/material_ui.dart';

import '../../../shared/widgets/dashboard_menu.dart';

class FacultyDashboardScreen extends StatelessWidget {
  const FacultyDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) => const DashboardMenu(
    title: 'Faculty Dashboard',
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
