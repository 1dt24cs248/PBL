import 'package:material_ui/material_ui.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:pbl/main.dart';
import 'package:pbl/features/authentication/authentication_screen.dart';

class FakeAuthNotifier extends AuthNotifier {
  FakeAuthNotifier(this.user);

  final AppUser? user;

  @override
  Future<AppUser?> build() async => user;
}

void main() {
  testWidgets('login form validates username and password', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authProvider.overrideWith(() => FakeAuthNotifier(null))],
        child: const MaterialApp(home: AuthenticationScreen()),
      ),
    );

    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Login'));
    await tester.tap(find.text('Login'));
    await tester.pump();

    expect(find.text('Enter your username or USN'), findsOneWidget);
    expect(find.text('Enter your password'), findsOneWidget);
  });

  final roleCases = <String, String>{
    'student': 'Student Dashboard',
    'teaching_faculty': 'Faculty Dashboard',
    'hod': 'HOD Dashboard',
    'admin': 'Management Dashboard',
    'maintenance': 'Management Dashboard',
  };

  for (final entry in roleCases.entries) {
    testWidgets('${entry.key} role redirects to ${entry.value}', (
      tester,
    ) async {
      final user = AppUser(
        id: 1,
        username: 'test-user',
        fullName: 'Test User',
        role: entry.key,
        category: entry.key == 'student' ? 'Student' : 'Faculty',
        department: 'CSE',
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [authProvider.overrideWith(() => FakeAuthNotifier(user))],
          child: const PblApp(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text(entry.value), findsWidgets);
    });
  }

  testWidgets('unauthenticated users redirect to login', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authProvider.overrideWith(() => FakeAuthNotifier(null))],
        child: const PblApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('DSATM Smart Campus'), findsWidgets);
  });
}
