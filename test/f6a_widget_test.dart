import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:pbl/core/config/app_config.dart';
import 'package:pbl/features/authentication/authentication_screen.dart';
import 'package:pbl/main.dart';

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier({this.user, this.loginCategory});

  AppUser? user;
  final String? loginCategory;
  String? selectedCategory;

  @override
  Future<AppUser?> build() async => user;

  @override
  Future<void> login(
    String username,
    String password, {
    required String selectedCategory,
  }) async {
    this.selectedCategory = selectedCategory;
    final category = loginCategory ?? selectedCategory;
    if (category != selectedCategory) {
      state = const AsyncData(null);
      throw AuthCategoryMismatch(category);
    }
    user = AppUser(
      id: 1,
      username: username,
      fullName: 'Test User',
      role: switch (category) {
        'Student' => 'student',
        'Faculty' => 'teaching_faculty',
        _ => 'admin',
      },
      category: category,
      department: 'CSE',
    );
    state = AsyncData(user);
  }
}

AppUser _user(String role) => AppUser(
  id: 1,
  username: 'test-user',
  fullName: 'Test User',
  role: role,
  category: switch (role) {
    'student' => 'Student',
    'admin' || 'maintenance' => 'Management',
    _ => 'Faculty',
  },
  department: 'CSE',
);

void main() {
  testWidgets('login role selector reports a backend category mismatch', (
    tester,
  ) async {
    final auth = _FakeAuthNotifier(loginCategory: 'Faculty');
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authProvider.overrideWith(() => auth)],
        child: const MaterialApp(home: AuthenticationScreen()),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('role_Student')));
    await tester.enterText(find.byKey(const Key('username_field')), 'fac1');
    await tester.enterText(find.byKey(const Key('password_field')), 'secret');
    await tester.ensureVisible(find.byKey(const Key('login_button')));
    await tester.tap(find.byKey(const Key('login_button')));
    await tester.pumpAndSettle();

    expect(auth.selectedCategory, 'Student');
    expect(
      find.text(
        'This account belongs to the Faculty category. Please select Faculty.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('password visibility toggle reveals and hides the password', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authProvider.overrideWith(() => _FakeAuthNotifier())],
        child: const MaterialApp(home: AuthenticationScreen()),
      ),
    );
    await tester.pumpAndSettle();

    final passwordInput = find.descendant(
      of: find.byKey(const Key('password_field')),
      matching: find.byType(EditableText),
    );
    expect(tester.widget<EditableText>(passwordInput).obscureText, isTrue);

    await tester.tap(find.byKey(const Key('password_visibility_toggle')));
    await tester.pump();

    expect(tester.widget<EditableText>(passwordInput).obscureText, isFalse);
  });

  testWidgets('forgot password shows configured help text', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authProvider.overrideWith(() => _FakeAuthNotifier())],
        child: const MaterialApp(home: AuthenticationScreen()),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('forgot_password')));
    await tester.pumpAndSettle();

    expect(find.text(AppConfig.passwordHelpText), findsOneWidget);
  });

  final roleTiles = <String, List<String>>{
    'student': [
      'Time Table',
      'Academic Calendar',
      'Attendance',
      'LMS',
      'Fees',
      'Profile',
      'Campus Map',
      'Route Navigator',
      'Room Finder',
      'Notifications',
    ],
    'teaching_faculty': [
      'Time Table',
      'Room Finder',
      'Campus Map',
      'Route Navigator',
      'Notifications',
    ],
    'hod': [
      'Time Table',
      'Room Finder',
      'Campus Map',
      'Route Navigator',
      'Notifications',
      'Energy',
    ],
    'admin': [
      'Energy',
      'Optimizer',
      'Proposals',
      'Room Finder',
      'Campus Map',
      'Route Navigator',
    ],
    'maintenance': ['Room Finder', 'Campus Map', 'Route Navigator'],
  };

  for (final entry in roleTiles.entries) {
    testWidgets('${entry.key} dashboard shows its feature tiles', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(1200, 2000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authProvider.overrideWith(
              () => _FakeAuthNotifier(user: _user(entry.key)),
            ),
          ],
          child: const PblApp(),
        ),
      );
      await tester.pumpAndSettle();

      for (final tile in entry.value) {
        expect(find.text(tile), findsWidgets, reason: 'Missing $tile');
      }
    });
  }
}
