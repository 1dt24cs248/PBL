import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import 'student_erp_models.dart';

const bool useMockStudentErpRepository = false;

abstract interface class StudentErpRepository {
  Future<StudentProfile> getProfile();
  Future<AttendanceData> getAttendance();
  Future<AttendanceSummary> getAttendanceSummary();
  Future<LmsSubjects> getLmsSubjects();
  Future<List<AcademicHoliday>> getHolidays();
  Future<StudentFees> getFees();
}

class ApiStudentErpRepository implements StudentErpRepository {
  const ApiStudentErpRepository(this.api);

  final ApiClient api;

  @override
  Future<StudentProfile> getProfile() async {
    final response = await api.dio.get<Map<String, dynamic>>(
      '/students/me/profile',
    );
    return StudentProfile.fromJson(response.data!);
  }

  @override
  Future<AttendanceData> getAttendance() async {
    final response = await api.dio.get<Map<String, dynamic>>(
      '/students/me/attendance',
    );
    return AttendanceData.fromJson(response.data!);
  }

  @override
  Future<AttendanceSummary> getAttendanceSummary() async {
    final response = await api.dio.get<Map<String, dynamic>>(
      '/students/me/attendance/summary',
    );
    return AttendanceSummary.fromJson(response.data!);
  }

  @override
  Future<LmsSubjects> getLmsSubjects() async {
    final response = await api.dio.get<Map<String, dynamic>>(
      '/students/me/lms/subjects',
    );
    return LmsSubjects.fromJson(response.data!);
  }

  @override
  Future<List<AcademicHoliday>> getHolidays() async {
    final response = await api.dio.get<List<dynamic>>('/calendar/holidays');
    return response.data!
        .map((item) => AcademicHoliday.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<StudentFees> getFees() async {
    final response = await api.dio.get<Map<String, dynamic>>(
      '/students/me/fees',
    );
    return StudentFees.fromJson(response.data!);
  }
}

class MockStudentErpRepository implements StudentErpRepository {
  Never _notConfigured() => throw UnsupportedError(
    'Mock student ERP mode is enabled, but no mock dataset is configured.',
  );

  @override
  Future<StudentProfile> getProfile() async => _notConfigured();
  @override
  Future<AttendanceData> getAttendance() async => _notConfigured();
  @override
  Future<AttendanceSummary> getAttendanceSummary() async => _notConfigured();
  @override
  Future<LmsSubjects> getLmsSubjects() async => _notConfigured();
  @override
  Future<List<AcademicHoliday>> getHolidays() async => _notConfigured();
  @override
  Future<StudentFees> getFees() async => _notConfigured();
}

final studentErpRepositoryProvider = Provider<StudentErpRepository>((ref) {
  if (useMockStudentErpRepository) return MockStudentErpRepository();
  return ApiStudentErpRepository(ref.watch(apiClientProvider));
});

final studentProfileProvider = FutureProvider<StudentProfile>(
  (ref) => ref.watch(studentErpRepositoryProvider).getProfile(),
  retry: (_, _) => null,
);
final attendanceDataProvider = FutureProvider<AttendanceData>(
  (ref) => ref.watch(studentErpRepositoryProvider).getAttendance(),
  retry: (_, _) => null,
);
final attendanceSummaryProvider = FutureProvider<AttendanceSummary>(
  (ref) => ref.watch(studentErpRepositoryProvider).getAttendanceSummary(),
  retry: (_, _) => null,
);
final lmsSubjectsProvider = FutureProvider<LmsSubjects>(
  (ref) => ref.watch(studentErpRepositoryProvider).getLmsSubjects(),
  retry: (_, _) => null,
);
final academicHolidaysProvider = FutureProvider<List<AcademicHoliday>>(
  (ref) => ref.watch(studentErpRepositoryProvider).getHolidays(),
  retry: (_, _) => null,
);
final studentFeesProvider = FutureProvider<StudentFees>(
  (ref) => ref.watch(studentErpRepositoryProvider).getFees(),
  retry: (_, _) => null,
);
