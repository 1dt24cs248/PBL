import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/authentication/authentication_screen.dart';
import '../../features/campus_map/campus_map_screen.dart';
import '../../features/dashboards/faculty/faculty_dashboard_screen.dart';
import '../../features/dashboards/hod/hod_dashboard_screen.dart';
import '../../features/dashboards/management/management_dashboard_screen.dart';
import '../../features/dashboards/student/student_dashboard_screen.dart';
import '../../features/events/events_screen.dart';
import '../../features/energy/energy_dashboard_screen.dart';
import '../../features/energy/optimizer_screen.dart';
import '../../features/energy/proposals_screen.dart';
import '../../features/extra_class_requests/extra_class_requests_screen.dart';
import '../../features/library/library_screen.dart';
import '../../features/maintenance/maintenance_screen.dart';
import '../../features/notifications/notifications_screen.dart';
import '../../features/resource_optimizer/resource_optimizer_screen.dart';
import '../../features/rooms/room_availability_screen.dart';
import '../../features/room_management/room_management_screen.dart';
import '../../features/timetable/timetable_screen.dart';
import '../../features/what_if_simulator/what_if_simulator_screen.dart';

String roleDashboardRoute(String role) => switch (role) {
  'student' => '/student',
  'teaching_faculty' => '/faculty',
  'hod' => '/hod',
  'admin' || 'maintenance' => '/management',
  _ => '/login',
};

String? energyRouteRedirect(String role, String location) {
  if (location == '/energy' && role != 'admin' && role != 'hod') {
    return roleDashboardRoute(role);
  }
  if (location == '/energy/optimizer' && role != 'admin') {
    return role == 'hod' ? '/energy' : roleDashboardRoute(role);
  }
  return null;
}

final appRouterProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authProvider);
  return GoRouter(
    initialLocation: '/login',
    refreshListenable: RouterRefreshNotifier(ref),
    redirect: (context, state) {
      if (auth.isLoading) return null;
      final user = auth.value;
      final loggingIn = state.matchedLocation == '/login';
      if (user == null) return loggingIn ? null : '/login';
      if (loggingIn) return roleDashboardRoute(user.role);
      return energyRouteRedirect(user.role, state.matchedLocation);
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const AuthenticationScreen(),
      ),
      GoRoute(
        path: '/student',
        builder: (context, state) => const StudentDashboardScreen(),
      ),
      GoRoute(
        path: '/student/timetable',
        builder: (context, state) => const TimetableScreen(),
      ),
      GoRoute(
        path: '/faculty/timetable',
        builder: (context, state) => const FacultyTimetableScreen(),
      ),
      GoRoute(
        path: '/rooms/availability',
        builder: (context, state) => const RoomAvailabilityScreen(),
      ),
      GoRoute(
        path: '/energy',
        builder: (context, state) => const EnergyDashboardScreen(),
      ),
      GoRoute(
        path: '/energy/optimizer',
        builder: (context, state) => const OptimizerScreen(),
      ),
      GoRoute(
        path: '/proposals',
        builder: (context, state) => const ProposalListScreen(),
      ),
      GoRoute(
        path: '/proposals/:proposalId',
        builder: (context, state) => ProposalDetailScreen(
          proposalId: state.pathParameters['proposalId']!,
        ),
      ),
      GoRoute(
        path: '/faculty',
        builder: (context, state) => const FacultyDashboardScreen(),
      ),
      GoRoute(
        path: '/hod',
        builder: (context, state) => const HodDashboardScreen(),
      ),
      GoRoute(
        path: '/management',
        builder: (context, state) => const ManagementDashboardScreen(),
      ),
      GoRoute(
        path: '/campus-map',
        builder: (context, state) => const CampusMapScreen(),
      ),
      GoRoute(
        path: '/route-navigator',
        builder: (context, state) => const RouteNavigatorScreen(),
      ),
      GoRoute(
        path: '/events',
        builder: (context, state) => const EventsScreen(),
      ),
      GoRoute(
        path: '/extra-class-requests',
        builder: (context, state) => const ExtraClassRequestsScreen(),
      ),
      GoRoute(
        path: '/library',
        builder: (context, state) => const LibraryScreen(),
      ),
      GoRoute(
        path: '/maintenance',
        builder: (context, state) => const MaintenanceScreen(),
      ),
      GoRoute(
        path: '/notifications',
        builder: (context, state) => const NotificationsScreen(),
      ),
      GoRoute(
        path: '/resource-optimizer',
        builder: (context, state) => const ResourceOptimizerScreen(),
      ),
      GoRoute(
        path: '/room-management',
        builder: (context, state) => const RoomManagementScreen(),
      ),
      GoRoute(
        path: '/what-if',
        builder: (context, state) => const WhatIfSimulatorScreen(),
      ),
    ],
  );
});

class RouterRefreshNotifier extends ChangeNotifier {
  RouterRefreshNotifier(this.ref) {
    ref.listen<AsyncValue<AppUser?>>(authProvider, (_, _) => notifyListeners());
  }

  final Ref ref;
}
