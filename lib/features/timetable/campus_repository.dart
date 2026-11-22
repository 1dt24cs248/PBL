import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';

const useMockTimetableRepository = false;

class TimetableSession {
  const TimetableSession({
    required this.id,
    required this.day,
    required this.periods,
    required this.subjectCode,
    required this.provenance,
    this.sectionCode,
    this.batch,
    this.subjectName,
    this.facultyInitials,
    this.facultyName,
    this.roomId,
    this.roomRequired,
    this.rawLabel,
    this.blockId,
    this.version,
    this.sessionType,
    this.startTime,
    this.endTime,
    this.facultyNames = const [],
    this.roomRealLabel,
    this.roomInferred,
  });

  factory TimetableSession.fromJson(Map<String, dynamic> json) =>
      TimetableSession(
        id: json['id'] as int,
        day: json['day'] as String,
        periods: (json['periods'] as List<dynamic>).cast<int>(),
        subjectCode: json['subject_code'] as String,
        provenance: json['provenance'] as String,
        sectionCode: json['section_code'] as String?,
        batch: json['batch'] as String?,
        subjectName: json['subject_name'] as String?,
        facultyInitials: json['faculty_initials'] as String?,
        facultyName: json['faculty_name'] as String?,
        roomId: json['room_id'] as String?,
        roomRequired: json['room_required'] as bool?,
        rawLabel: json['raw_label'] as String?,
        blockId: json['block_id'] as String?,
        version: json['version'] as int?,
        sessionType: json['session_type'] as String?,
        startTime: json['start_time'] as String?,
        endTime: json['end_time'] as String?,
        facultyNames: (json['faculty_names'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
        roomRealLabel: json['room_real_label'] as String?,
        roomInferred: json['room_inferred'] as bool?,
      );

  final int id;
  final String day;
  final List<int> periods;
  final String subjectCode;
  final String provenance;
  final String? sectionCode;
  final String? batch;
  final String? subjectName;
  final String? facultyInitials;
  final String? facultyName;
  final String? roomId;
  final bool? roomRequired;
  final String? rawLabel;
  final String? blockId;
  final int? version;
  final String? sessionType;
  final String? startTime;
  final String? endTime;
  final List<String> facultyNames;
  final String? roomRealLabel;
  final bool? roomInferred;
}

class StudentTimetable {
  const StudentTimetable({
    required this.usn,
    required this.termCode,
    required this.divisionCode,
    required this.sectionCode,
    required this.labBatch,
    required this.sessions,
  });

  factory StudentTimetable.fromJson(Map<String, dynamic> json) =>
      StudentTimetable(
        usn: json['usn'] as String,
        termCode: json['term_code'] as String,
        divisionCode: json['division_code'] as String,
        sectionCode: json['section_code'] as String,
        labBatch: json['lab_batch'] as String,
        sessions: (json['sessions'] as List<dynamic>)
            .map(
              (item) => TimetableSession.fromJson(item as Map<String, dynamic>),
            )
            .toList(),
      );

  final String usn;
  final String termCode;
  final String divisionCode;
  final String sectionCode;
  final String labBatch;
  final List<TimetableSession> sessions;
}

class FacultyTimetable {
  const FacultyTimetable({required this.sessions});

  factory FacultyTimetable.fromJson(Map<String, dynamic> json) =>
      FacultyTimetable(
        sessions: (json['sessions'] as List<dynamic>)
            .map(
              (item) => TimetableSession.fromJson(item as Map<String, dynamic>),
            )
            .toList(),
      );

  final List<TimetableSession> sessions;
}

class TimetableDate {
  const TimetableDate({
    required this.date,
    required this.weekday,
    required this.holiday,
    required this.sessions,
  });

  factory TimetableDate.fromJson(Map<String, dynamic> json) => TimetableDate(
    date: json['date'] as String,
    weekday: json['weekday'] as String,
    holiday: json['holiday'] as String?,
    sessions: (json['sessions'] as List<dynamic>)
        .map((item) => TimetableSession.fromJson(item as Map<String, dynamic>))
        .toList(),
  );

  final String date;
  final String weekday;
  final String? holiday;
  final List<TimetableSession> sessions;
}

class RoomMetadata {
  const RoomMetadata({
    required this.number,
    required this.floor,
    required this.dataStatus,
    this.realLabel,
    this.floorName,
    this.capacity,
    this.capacityEffective,
  });

  factory RoomMetadata.fromJson(Map<String, dynamic> json) => RoomMetadata(
    number: json['number'] as String,
    floor: json['floor'] as int,
    dataStatus: json['data_status'] as String,
    realLabel: json['real_label'] as String?,
    floorName: json['floor_name'] as String?,
    capacity: (json['capacity'] as num?)?.toInt(),
    capacityEffective: (json['capacity_effective'] as num?)?.toInt(),
  );

  final String number;
  final int floor;
  final String dataStatus;
  final String? realLabel;
  final String? floorName;
  final int? capacity;
  final int? capacityEffective;

  int? get effectiveCapacity => capacityEffective ?? capacity;
}

class RoomAvailabilityItem {
  const RoomAvailabilityItem({
    required this.roomId,
    required this.available,
    this.dataStatus,
    this.provenance,
    this.floor,
    this.capacity,
    this.capacityEffective,
  });

  factory RoomAvailabilityItem.fromJson(Map<String, dynamic> json) =>
      RoomAvailabilityItem(
        roomId: (json['room_id'] ?? json['number']) as String,
        available: json['available'] as bool,
        dataStatus: json['data_status'] as String?,
        provenance: json['provenance'] as String?,
        floor: json['floor'] as int?,
        capacity: (json['capacity'] as num?)?.toInt(),
        capacityEffective: (json['capacity_effective'] as num?)?.toInt(),
      );

  final String roomId;
  final bool available;
  final String? dataStatus;
  final String? provenance;
  final int? floor;
  final int? capacity;
  final int? capacityEffective;
}

class AvailableRoom {
  const AvailableRoom({
    required this.number,
    required this.available,
    required this.dataStatus,
    this.realLabel,
    this.floor,
    this.floorName,
    this.capacity,
  });

  final String number;
  final bool available;
  final String? dataStatus;
  final String? realLabel;
  final int? floor;
  final String? floorName;
  final int? capacity;
}

class MetaPeriod {
  const MetaPeriod({
    required this.period,
    required this.start,
    required this.end,
  });

  factory MetaPeriod.fromJson(Map<String, dynamic> json) => MetaPeriod(
    period: json['period'] as int,
    start: json['start'] as String,
    end: json['end'] as String,
  );

  final int period;
  final String start;
  final String end;
}

class PeriodBreak {
  const PeriodBreak({
    required this.afterPeriod,
    required this.label,
    required this.start,
    required this.end,
  });

  factory PeriodBreak.fromJson(Map<String, dynamic> json) => PeriodBreak(
    afterPeriod: json['after_period'] as int,
    label: json['label'] as String,
    start: json['start'] as String,
    end: json['end'] as String,
  );

  final int afterPeriod;
  final String label;
  final String start;
  final String end;
}

class TimetableMeta {
  const TimetableMeta({required this.periods, required this.breaks});

  factory TimetableMeta.fromJson(Map<String, dynamic> json) => TimetableMeta(
    periods: (json['periods'] as List<dynamic>)
        .map((item) => MetaPeriod.fromJson(item as Map<String, dynamic>))
        .toList(),
    breaks: (json['breaks'] as List<dynamic>)
        .map((item) => PeriodBreak.fromJson(item as Map<String, dynamic>))
        .toList(),
  );

  final List<MetaPeriod> periods;
  final List<PeriodBreak> breaks;
}

class CalendarHoliday {
  const CalendarHoliday({
    required this.date,
    required this.name,
    required this.source,
  });

  factory CalendarHoliday.fromJson(Map<String, dynamic> json) =>
      CalendarHoliday(
        date: json['date'] as String,
        name: json['name'] as String,
        source: json['source'] as String,
      );

  final String date;
  final String name;
  final String source;
}

class TimetableFailure implements Exception {
  const TimetableFailure(this.statusCode, this.message);

  final int? statusCode;
  final String message;

  bool get isNetworkError {
    final status = statusCode;
    return status == null || status >= 500;
  }

  factory TimetableFailure.from(Object error) {
    if (error is TimetableFailure) return error;
    if (error is DioException) {
      final status = error.response?.statusCode;
      final responseData = error.response?.data;
      final detail = responseData is Map<String, dynamic>
          ? responseData['detail']
          : null;
      final message = switch (detail) {
        List<dynamic> values =>
          values
              .map((item) {
                if (item is Map<String, dynamic>) {
                  return item['msg']?.toString();
                }
                return item.toString();
              })
              .whereType<String>()
              .join('; '),
        null => null,
        _ => detail.toString(),
      };
      return TimetableFailure(
        status,
        message ?? error.message ?? 'Request failed',
      );
    }
    return TimetableFailure(null, error.toString());
  }
}

abstract interface class CampusRepository {
  Future<StudentTimetable> getStudentTimetable();
  Future<FacultyTimetable> getFacultyTimetable({String? day});
  Future<TimetableDate> getTimetableDate(String date);
  Future<List<AvailableRoom>> getAvailableRooms({
    required String day,
    required int period,
  });
  Future<TimetableMeta> getTimetableMeta();
  Future<List<CalendarHoliday>> getCalendarHolidays();
}

class ApiCampusRepository implements CampusRepository {
  ApiCampusRepository(this.api);

  final ApiClient api;

  @override
  Future<StudentTimetable> getStudentTimetable() async {
    final response = await api.dio.get<Map<String, dynamic>>(
      '/timetable/student/me',
    );
    return StudentTimetable.fromJson(response.data!);
  }

  @override
  Future<FacultyTimetable> getFacultyTimetable({String? day}) async {
    final response = await api.dio.get<Map<String, dynamic>>(
      '/timetable/faculty/me',
      queryParameters: day == null ? null : {'day': day},
    );
    return FacultyTimetable.fromJson(response.data!);
  }

  @override
  Future<TimetableDate> getTimetableDate(String date) async {
    final response = await api.dio.get<Map<String, dynamic>>(
      '/timetable/date/$date',
    );
    return TimetableDate.fromJson(response.data!);
  }

  @override
  Future<List<AvailableRoom>> getAvailableRooms({
    required String day,
    required int period,
  }) async {
    final responses = await Future.wait([
      api.dio.get<Map<String, dynamic>>(
        '/rooms/availability',
        queryParameters: {'day': day, 'period': period},
      ),
      api.dio.get<List<dynamic>>('/rooms'),
    ]);
    final availabilityJson = responses[0].data as Map<String, dynamic>;
    final roomJson = responses[1].data as List<dynamic>;
    final roomMetadata = {
      for (final item in roomJson)
        (item as Map<String, dynamic>)['number'] as String:
            RoomMetadata.fromJson(item),
    };
    final availability = (availabilityJson['rooms'] as List<dynamic>)
        .map(
          (item) => RoomAvailabilityItem.fromJson(item as Map<String, dynamic>),
        )
        .where((room) => room.available);
    return availability.map((room) {
      final metadata = roomMetadata[room.roomId];
      return AvailableRoom(
        number: room.roomId,
        available: room.available,
        dataStatus: room.dataStatus ?? metadata?.dataStatus,
        realLabel: metadata?.realLabel,
        floor: room.floor ?? metadata?.floor,
        floorName: metadata?.floorName,
        capacity:
            room.capacityEffective ??
            room.capacity ??
            metadata?.effectiveCapacity,
      );
    }).toList();
  }

  @override
  Future<TimetableMeta> getTimetableMeta() async {
    final response = await api.dio.get<Map<String, dynamic>>('/meta/periods');
    return TimetableMeta.fromJson(response.data!);
  }

  @override
  Future<List<CalendarHoliday>> getCalendarHolidays() async {
    final response = await api.dio.get<List<dynamic>>('/calendar/holidays');
    return response.data!
        .map((item) => CalendarHoliday.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}

class MockCampusRepository implements CampusRepository {
  @override
  Future<StudentTimetable> getStudentTimetable() async =>
      const StudentTimetable(
        usn: '',
        termCode: '',
        divisionCode: '',
        sectionCode: '',
        labBatch: '',
        sessions: [],
      );

  @override
  Future<FacultyTimetable> getFacultyTimetable({String? day}) async =>
      const FacultyTimetable(sessions: []);

  @override
  Future<TimetableDate> getTimetableDate(String date) async =>
      TimetableDate(date: date, weekday: '', holiday: null, sessions: const []);

  @override
  Future<List<AvailableRoom>> getAvailableRooms({
    required String day,
    required int period,
  }) async => [];

  @override
  Future<TimetableMeta> getTimetableMeta() async =>
      const TimetableMeta(periods: [], breaks: []);

  @override
  Future<List<CalendarHoliday>> getCalendarHolidays() async => const [];
}

final campusRepositoryProvider = Provider<CampusRepository>((ref) {
  if (useMockTimetableRepository) return MockCampusRepository();
  return ApiCampusRepository(ref.watch(apiClientProvider));
});

final studentTimetableProvider = FutureProvider<StudentTimetable>(
  (ref) => ref.watch(campusRepositoryProvider).getStudentTimetable(),
  retry: (_, _) => null,
);

final facultyTimetableProvider =
    FutureProvider.family<FacultyTimetable, String?>(
      (ref, day) =>
          ref.watch(campusRepositoryProvider).getFacultyTimetable(day: day),
      retry: (_, _) => null,
    );

final timetableDateProvider = FutureProvider.family<TimetableDate, String>(
  (ref, date) => ref.watch(campusRepositoryProvider).getTimetableDate(date),
  retry: (_, _) => null,
);

typedef AvailabilityQuery = ({String day, int period});

final roomAvailabilityProvider =
    FutureProvider.family<List<AvailableRoom>, AvailabilityQuery>(
      (ref, query) => ref
          .watch(campusRepositoryProvider)
          .getAvailableRooms(day: query.day, period: query.period),
      retry: (_, _) => null,
    );

final timetableMetaProvider = FutureProvider<TimetableMeta>(
  (ref) => ref.watch(campusRepositoryProvider).getTimetableMeta(),
  retry: (_, _) => null,
);

final calendarHolidaysProvider = FutureProvider<List<CalendarHoliday>>(
  (ref) => ref.watch(campusRepositoryProvider).getCalendarHolidays(),
  retry: (_, _) => null,
);
