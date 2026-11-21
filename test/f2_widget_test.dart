import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:pbl/features/rooms/room_availability_screen.dart';
import 'package:pbl/features/timetable/campus_repository.dart';
import 'package:pbl/features/timetable/timetable_screen.dart';

class FakeCampusRepository implements CampusRepository {
  FakeCampusRepository({
    this.studentResult,
    this.facultyResult,
    this.dateResult,
    this.roomsResult,
  });

  final Future<StudentTimetable> Function()? studentResult;
  final Future<FacultyTimetable> Function(String? day)? facultyResult;
  final Future<TimetableDate> Function(String date)? dateResult;
  final Future<List<AvailableRoom>> Function(String day, int period)?
  roomsResult;
  final requestedDates = <String>[];
  final requestedRoomQueries = <({String day, int period})>[];

  @override
  Future<StudentTimetable> getStudentTimetable() =>
      studentResult?.call() ?? Future.value(_emptyStudentTimetable);

  @override
  Future<FacultyTimetable> getFacultyTimetable({String? day}) =>
      facultyResult?.call(day) ??
      Future.value(const FacultyTimetable(sessions: []));

  @override
  Future<TimetableDate> getTimetableDate(String date) {
    requestedDates.add(date);
    return dateResult?.call(date) ??
        Future.value(
          TimetableDate(
            date: date,
            weekday: 'Tue',
            holiday: null,
            sessions: const [],
          ),
        );
  }

  @override
  Future<List<AvailableRoom>> getAvailableRooms({
    required String day,
    required int period,
  }) {
    requestedRoomQueries.add((day: day, period: period));
    return roomsResult?.call(day, period) ?? Future.value([]);
  }
}

const _emptyStudentTimetable = StudentTimetable(
  usn: 'test',
  termCode: '2026-27-ODD',
  divisionCode: 'CSE-5',
  sectionCode: 'E',
  labBatch: 'A1',
  sessions: [],
);

void main() {
  testWidgets('student timetable shows holiday returned for selected date', (
    tester,
  ) async {
    final repository = FakeCampusRepository(
      dateResult: (date) async => TimetableDate(
        date: date,
        weekday: 'Tue',
        holiday: 'Deepavali 2026',
        sessions: const [],
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [campusRepositoryProvider.overrideWithValue(repository)],
        child: MaterialApp(
          home: TimetableScreen(initialDate: DateTime(2026, 11, 10)),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Deepavali'), findsOneWidget);
    expect(repository.requestedDates, ['2026-11-10']);
  });

  testWidgets('student timetable offers retry after a network error', (
    tester,
  ) async {
    var attempts = 0;
    final repository = FakeCampusRepository(
      studentResult: () async {
        attempts++;
        if (attempts == 1) {
          throw const TimetableFailure(null, 'Connection failed');
        }
        return _emptyStudentTimetable;
      },
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [campusRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: TimetableScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(attempts, 1);
    expect(find.text('Network error. Check your connection.'), findsOneWidget);
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();

    expect(attempts, 2);
    expect(
      find.text('No timetable sessions for this selection.'),
      findsOneWidget,
    );
  });

  testWidgets('faculty timetable presents a clean not-found state', (
    tester,
  ) async {
    final repository = FakeCampusRepository(
      facultyResult: (_) async =>
          throw const TimetableFailure(404, 'Not found'),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [campusRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: FacultyTimetableScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Faculty timetable is unavailable for this account.'),
      findsOneWidget,
    );
  });

  testWidgets('403 responses show an access-denied state', (tester) async {
    final repository = FakeCampusRepository(
      studentResult: () async =>
          throw const TimetableFailure(403, 'Insufficient permissions'),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [campusRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: TimetableScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('You do not have permission to view this data.'),
      findsOneWidget,
    );
    expect(find.text('Retry'), findsNothing);
  });

  testWidgets('availability finder filters by capacity and shows API status', (
    tester,
  ) async {
    final repository = FakeCampusRepository(
      roomsResult: (day, period) async => [
        const AvailableRoom(
          number: 'A-F1-01',
          available: true,
          dataStatus: 'SYNTHETIC',
          realLabel: "101 'A' BLOCK",
          floor: 1,
          floorName: 'First Floor',
          capacity: 40,
        ),
        const AvailableRoom(
          number: 'A-F1-02',
          available: true,
          dataStatus: 'INFERRED',
          floor: 1,
          floorName: 'First Floor',
          capacity: 80,
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [campusRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: RoomAvailabilityScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Synthetic'), findsOneWidget);
    expect(find.text('Inferred'), findsOneWidget);
    expect(find.text('A-F1-01'), findsOneWidget);
    expect(find.text('A-F1-02'), findsOneWidget);

    await tester.enterText(
      find.byKey(const Key('minimum_capacity_field')),
      '50',
    );
    await tester.pumpAndSettle();

    expect(find.text('A-F1-01'), findsNothing);
    expect(find.text('A-F1-02'), findsOneWidget);
    expect(repository.requestedRoomQueries.first, (day: 'Mon', period: 1));
  });
}
