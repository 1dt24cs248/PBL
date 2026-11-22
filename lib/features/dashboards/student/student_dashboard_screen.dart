import 'package:material_ui/material_ui.dart';

import '../../../shared/widgets/dashboard_menu.dart';

class StudentDashboardScreen extends StatelessWidget {
  const StudentDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) => const DashboardMenu(
    title: 'Student Dashboard',
    showStudentMetadata: true,
    destinations: [
      DashboardDestination(
        title: 'Time Table',
        subtitle: "Today's timetable",
        route: '/student/timetable',
        icon: Icons.calendar_month_outlined,
      ),
      DashboardDestination(
        title: 'Academic Calendar',
        route: '/student/calendar',
        icon: Icons.event_note_outlined,
      ),
      DashboardDestination(
        title: 'Attendance',
        route: '/student/attendance',
        icon: Icons.fact_check_outlined,
      ),
      DashboardDestination(
        title: 'LMS',
        route: '/student/lms',
        icon: Icons.menu_book_outlined,
      ),
      DashboardDestination(
        title: 'Fees',
        route: '/student/fees',
        icon: Icons.receipt_long_outlined,
      ),
      DashboardDestination(
        title: 'Profile',
        route: '/student/profile',
        icon: Icons.person_outline,
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
        title: 'Room Finder',
        route: '/rooms/availability',
        icon: Icons.meeting_room_outlined,
      ),
      DashboardDestination(
        title: 'Notifications',
        route: '/notifications',
        icon: Icons.notifications_outlined,
      ),
    ],
  );
}
