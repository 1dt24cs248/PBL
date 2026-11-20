// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';
import 'package:pbl/main.dart';

void main() {
  testWidgets('PBL home shows the app title and health check', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(PblApp(healthCheck: () async => 'ok'));
    await tester.pump();

    expect(find.text('PBL Campus'), findsOneWidget);
    expect(find.text('Backend status: ok'), findsOneWidget);
  });
}
