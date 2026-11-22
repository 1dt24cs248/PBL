import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:pbl/features/student_erp/student_erp_models.dart';
import 'package:pbl/features/student_erp/student_erp_repository.dart';
import 'package:pbl/features/student_erp/student_erp_screens.dart';

class FakeStudentErpRepository implements StudentErpRepository {
  @override
  Future<StudentProfile> getProfile() async => const StudentProfile(
    usn: '1DT24CS248',
    fullName: 'Test Student',
    branch: 'CS',
    department: 'CSE',
    semester: 5,
    division: 'CSE-5',
    sectionLabel: 'CS-5-E',
    sectionMappingStatus: 'INFERRED',
    labBatch: 'A1',
    rollNo: null,
    homeRoom: StudentHomeRoom(code: 'A-F5-02', realLabel: 'Classroom 02'),
    dataStatus: 'SYNTHETIC',
  );

  @override
  Future<AttendanceData> getAttendance() async => const AttendanceData(
    dataStatus: 'SYNTHETIC',
    days: [
      AttendanceDay(
        date: '2026-11-20',
        weekday: 'Fri',
        slots: [
          AttendanceSlot(
            slot: 'P1',
            subjectCode: 'BCS515B',
            subjectName: 'Cryptography',
            status: 'P',
          ),
        ],
      ),
    ],
  );

  @override
  Future<AttendanceSummary> getAttendanceSummary() async =>
      const AttendanceSummary(
        dataStatus: 'SYNTHETIC',
        overall: AttendanceOverall(
          present: 1,
          absent: 1,
          noAttendance: 0,
          total: 2,
          percent: 50,
        ),
        subjects: [
          AttendanceSubject(
            subjectCode: 'BCS515B',
            subjectName: 'Cryptography',
            component: 'Theory',
            total: 2,
            present: 1,
            percent: 50,
            status: 'low',
          ),
        ],
      );

  @override
  Future<LmsSubjects> getLmsSubjects() async => const LmsSubjects(
    dataStatus: 'SYNTHETIC',
    subjects: [
      LmsSubject(
        subjectCode: 'BCS515B',
        altCode: 'BCS504B',
        subjectName: 'Cryptography & Network Security',
        component: 'Theory',
        semester: 5,
        facultyNames: ['Test Faculty'],
      ),
    ],
  );

  @override
  Future<List<AcademicHoliday>> getHolidays() async => const [
    AcademicHoliday(date: '2026-11-10', name: 'Deepavali 2026', source: 'M1'),
  ];

  @override
  Future<StudentFees> getFees() async => const StudentFees(
    dataStatus: 'SYNTHETIC',
    ledger: FeesLedger(
      toBeCollected: 360000,
      paid: 240000,
      previous: 0,
      pending: 120000,
    ),
    years: [
      FeesYear(
        year: 1,
        total: 120000,
        receipts: [
          FeeReceipt(
            receiptNo: 'SYN-0001',
            date: '2024-06-01',
            heads: [FeeHead(name: 'Tuition', amount: 120000)],
            mode: 'SYNTHETIC',
          ),
        ],
      ),
    ],
    scholarship: FeesScholarship(
      status: 'Not applicable',
      note: 'Synthetic demo',
    ),
  );
}

Widget _harness(Widget child) => ProviderScope(
  overrides: [
    studentErpRepositoryProvider.overrideWithValue(FakeStudentErpRepository()),
  ],
  child: MaterialApp(home: child),
);

void main() {
  testWidgets('student profile shows synthetic banner and inferred mapping', (
    tester,
  ) async {
    await tester.pumpWidget(_harness(const StudentProfileScreen()));
    await tester.pumpAndSettle();

    expect(find.text('Demo data (synthetic)'), findsOneWidget);
    expect(find.text('1DT24CS248'), findsOneWidget);
    expect(find.text('Section mapping is inferred.'), findsOneWidget);
  });

  testWidgets('attendance subject progress uses 75 percent red threshold', (
    tester,
  ) async {
    await tester.pumpWidget(_harness(const AttendanceScreen()));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Subject-wise'));
    await tester.pumpAndSettle();

    expect(find.text('50.0%'), findsOneWidget);
  });

  testWidgets('LMS search filters subject cards', (tester) async {
    await tester.pumpWidget(_harness(const LmsScreen()));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('lms_search')), 'Cryptography');
    await tester.pumpAndSettle();
    expect(find.textContaining('Cryptography'), findsWidgets);
  });

  testWidgets('fees shows synthetic ledger and expandable year', (
    tester,
  ) async {
    await tester.pumpWidget(_harness(const StudentFeesScreen()));
    await tester.pumpAndSettle();

    expect(find.text('Demo data (synthetic)'), findsOneWidget);
    expect(find.text('₹360000'), findsOneWidget);
    expect(find.text('Year 1'), findsOneWidget);
  });

  testWidgets('calendar displays API holiday and unknown term dates', (
    tester,
  ) async {
    await tester.pumpWidget(_harness(const AcademicCalendarScreen()));
    await tester.pumpAndSettle();

    expect(find.text('Deepavali 2026'), findsOneWidget);
    expect(find.text('Term dates not loaded'), findsOneWidget);
  });
}
