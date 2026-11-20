import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';

const useMockTimetableRepository = true;

class StudentTimetableSession {
  const StudentTimetableSession({
    required this.id,
    required this.day,
    required this.periods,
    required this.subjectCode,
    required this.subjectName,
    required this.facultyInitials,
    required this.roomId,
    required this.batch,
    required this.roomRequired,
    required this.rawLabel,
    required this.blockId,
    required this.provenance,
    required this.version,
    this.facultyName,
    this.roomCode,
    this.realLabel,
    this.roomInferred = false,
    this.dataStatus,
  });

  factory StudentTimetableSession.fromJson(Map<String, dynamic> json) =>
      StudentTimetableSession(
        id: json['id'] as int,
        day: json['day'] as String,
        periods: (json['periods'] as List<dynamic>).cast<int>(),
        subjectCode: json['subject_code'] as String,
        subjectName: json['subject_name'] as String? ?? '',
        facultyInitials: json['faculty_initials'] as String? ?? '',
        roomId: json['room_id'] as String?,
        batch: json['batch'] as String,
        roomRequired: json['room_required'] as bool,
        rawLabel: json['raw_label'] as String?,
        blockId: json['block_id'] as String?,
        provenance: json['provenance'] as String,
        version: json['version'] as int,
        facultyName: json['faculty_name'] as String?,
        roomCode: json['room_code'] as String?,
        realLabel: json['real_label'] as String?,
        roomInferred: json['room_inferred'] as bool? ?? false,
        dataStatus: json['data_status'] as String?,
      );

  final int id;
  final String day;
  final List<int> periods;
  final String subjectCode;
  final String subjectName;
  final String facultyInitials;
  final String? roomId;
  final String batch;
  final bool roomRequired;
  final String? rawLabel;
  final String? blockId;
  final String provenance;
  final int version;
  final String? facultyName;
  final String? roomCode;
  final String? realLabel;
  final bool roomInferred;
  final String? dataStatus;

  bool get isInferred =>
      roomInferred || provenance == 'INFERRED' || dataStatus == 'INFERRED';

  String get facultyLabel => facultyName != null && facultyName!.isNotEmpty
      ? '$facultyName (${facultyInitials.isEmpty ? '-' : facultyInitials})'
      : facultyInitials;
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
              (item) => StudentTimetableSession.fromJson(
                item as Map<String, dynamic>,
              ),
            )
            .toList(),
      );

  final String usn;
  final String termCode;
  final String divisionCode;
  final String sectionCode;
  final String labBatch;
  final List<StudentTimetableSession> sessions;
}

abstract interface class StudentTimetableRepository {
  Future<StudentTimetable> getStudentTimetable();
}

class ApiStudentTimetableRepository implements StudentTimetableRepository {
  ApiStudentTimetableRepository(this.api);

  final ApiClient api;

  @override
  Future<StudentTimetable> getStudentTimetable() async {
    final response = await api.dio.get<Map<String, dynamic>>(
      '/timetable/student/me',
    );
    return StudentTimetable.fromJson(response.data!);
  }
}

class MockStudentTimetableRepository implements StudentTimetableRepository {
  @override
  Future<StudentTimetable> getStudentTimetable() async {
    return const StudentTimetable(
      usn: 'MOCK-USN',
      termCode: 'MOCK-OFFLINE',
      divisionCode: 'MOCK',
      sectionCode: 'MOCK',
      labBatch: 'MOCK',
      sessions: [],
    );
  }
}

final studentTimetableRepositoryProvider = Provider<StudentTimetableRepository>(
  (ref) {
    if (useMockTimetableRepository) {
      return MockStudentTimetableRepository();
    }
    return ApiStudentTimetableRepository(ref.watch(apiClientProvider));
  },
);

final studentTimetableProvider =
    AsyncNotifierProvider<StudentTimetableNotifier, StudentTimetable?>(
      StudentTimetableNotifier.new,
    );

class StudentTimetableNotifier extends AsyncNotifier<StudentTimetable?> {
  @override
  Future<StudentTimetable?> build() async {
    final repository = ref.read(studentTimetableRepositoryProvider);
    return repository.getStudentTimetable();
  }
}

class TimetableScreen extends ConsumerStatefulWidget {
  const TimetableScreen({super.key});

  @override
  ConsumerState<TimetableScreen> createState() => _TimetableScreenState();
}

class _TimetableScreenState extends ConsumerState<TimetableScreen> {
  String _week = 'All weeks';
  String _day = 'All';

  static const _days = ['All', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  @override
  Widget build(BuildContext context) {
    final timetable = ref.watch(studentTimetableProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Student Timetable')),
      body: Column(
        children: [
          if (useMockTimetableRepository)
            Container(
              width: double.infinity,
              color: Colors.amber.shade100,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: const Text(
                'OFFLINE MOCK DATA',
                textAlign: TextAlign.center,
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: _week,
                    decoration: const InputDecoration(labelText: 'Week'),
                    items:
                        [
                              'All weeks',
                              for (var week = 1; week <= 6; week++)
                                'Week $week',
                            ]
                            .map(
                              (week) => DropdownMenuItem(
                                value: week,
                                child: Text(week),
                              ),
                            )
                            .toList(),
                    onChanged: (value) {
                      if (value != null) setState(() => _week = value);
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: _day,
                    decoration: const InputDecoration(labelText: 'Day'),
                    items: _days
                        .map(
                          (day) =>
                              DropdownMenuItem(value: day, child: Text(day)),
                        )
                        .toList(),
                    onChanged: (value) {
                      if (value != null) setState(() => _day = value);
                    },
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: timetable.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => Center(
                child: Text(
                  'Unable to load timetable',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              data: (data) {
                if (data == null) {
                  return const Center(child: Text('No timetable data.'));
                }
                final sessions =
                    data.sessions
                        .where(
                          (session) => _day == 'All' || session.day == _day,
                        )
                        .toList()
                      ..sort(
                        (a, b) => a.day.compareTo(b.day) == 0
                            ? (a.periods.isEmpty ? 0 : a.periods.first)
                                  .compareTo(
                                    b.periods.isEmpty ? 0 : b.periods.first,
                                  )
                            : a.day.compareTo(b.day),
                      );
                if (sessions.isEmpty) {
                  return const Center(child: Text('No timetable sessions.'));
                }
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  itemCount: sessions.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final session = sessions[index];
                    final roomCode = session.roomCode ?? session.roomId ?? '-';
                    final roomLabel = session.realLabel?.isNotEmpty == true
                        ? '$roomCode · ${session.realLabel}'
                        : roomCode;
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              children: [
                                Text(
                                  '${session.day} · ${_periodText(session.periods)}',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                if (session.isInferred)
                                  Chip(
                                    label: const Text('Inferred'),
                                    visualDensity: VisualDensity.compact,
                                    backgroundColor: Colors.amber.shade100,
                                  ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              session.subjectName.isEmpty
                                  ? session.subjectCode
                                  : '${session.subjectCode} · ${session.subjectName}',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Faculty: ${session.facultyLabel.isEmpty ? '-' : session.facultyLabel}',
                            ),
                            Text('Room: $roomLabel'),
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  String _periodText(List<int> periods) {
    if (periods.isEmpty) return 'Period';
    if (periods.length == 1) return 'Period ${periods.first}';
    return 'Periods ${periods.join('-')}';
  }
}
