import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/widgets/api_error_view.dart';
import '../../shared/widgets/dashboard_components.dart';
import 'student_erp_models.dart';
import 'student_erp_repository.dart';

class StudentProfileScreen extends ConsumerWidget {
  const StudentProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(studentProfileProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: profile.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ApiErrorView(
          error: error,
          onRetry: () => ref.invalidate(studentProfileProvider),
        ),
        data: (value) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const DemoDataBanner(),
            const SizedBox(height: 12),
            SectionCard(
              title: 'Student Profile',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    value.fullName,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  Text(value.usn),
                  const SizedBox(height: 12),
                  Text('Branch: ${value.branch}'),
                  Text('Department: ${value.department}'),
                  Text('Semester: ${value.semester}'),
                  Text('Division: ${value.division}'),
                  Text('Section: ${value.sectionLabel}'),
                  Text('Lab batch: ${value.labBatch}'),
                  Text('Roll No.: ${value.rollNo ?? '-'}'),
                  Text(
                    'Home room: ${value.homeRoom.realLabel} '
                    '(${value.homeRoom.code})',
                  ),
                  if (value.sectionMappingStatus == 'INFERRED')
                    const Padding(
                      padding: EdgeInsets.only(top: 8),
                      child: Text(
                        'Section mapping is inferred.',
                        style: TextStyle(color: Color(0xFFEA580C)),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class AttendanceScreen extends ConsumerWidget {
  const AttendanceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => DefaultTabController(
    length: 2,
    child: Scaffold(
      appBar: AppBar(
        title: const Text('Attendance'),
        bottom: const TabBar(
          tabs: [
            Tab(text: 'Daily'),
            Tab(text: 'Subject-wise'),
          ],
        ),
      ),
      body: Column(
        children: [
          const Padding(padding: EdgeInsets.all(16), child: DemoDataBanner()),
          Expanded(
            child: TabBarView(
              children: [_DailyAttendanceView(), _SubjectAttendanceView()],
            ),
          ),
        ],
      ),
    ),
  );
}

class _DailyAttendanceView extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final grid = ref.watch(attendanceDataProvider);
    final summary = ref.watch(attendanceSummaryProvider);
    return grid.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => ApiErrorView(
        error: error,
        onRetry: () => ref.invalidate(attendanceDataProvider),
      ),
      data: (data) => ListView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        children: [
          summary.when(
            loading: () => const SizedBox.shrink(),
            error: (_, _) => const SizedBox.shrink(),
            data: (value) => Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${value.overall.percent.toStringAsFixed(1)}%',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 8),
                    LinearProgressIndicator(
                      value: value.overall.percent / 100,
                      color: value.overall.percent < 75
                          ? const Color(0xFFDC2626)
                          : const Color(0xFF16A34A),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Present ${value.overall.present} / '
                      'Absent ${value.overall.absent} / '
                      'Pending ${value.overall.noAttendance}',
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 12),
          for (final day in data.days)
            Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${day.date} · ${day.weekday}',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        for (final slot in day.slots)
                          _AttendanceSlotChip(slot: slot),
                      ],
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _AttendanceSlotChip extends StatelessWidget {
  const _AttendanceSlotChip({required this.slot});
  final AttendanceSlot slot;

  @override
  Widget build(BuildContext context) {
    final color = switch (slot.status) {
      'P' => const Color(0xFF16A34A),
      'A' => const Color(0xFFDC2626),
      'NA' => const Color(0xFF2563EB),
      _ => const Color(0xFF64748B),
    };
    final background = color.withValues(alpha: 0.12);
    return Container(
      constraints: const BoxConstraints(minWidth: 58),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Text(slot.slot ?? '-', style: const TextStyle(fontSize: 11)),
          Text(
            slot.status,
            style: TextStyle(color: color, fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }
}

class _SubjectAttendanceView extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(attendanceSummaryProvider);
    return summary.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => ApiErrorView(
        error: error,
        onRetry: () => ref.invalidate(attendanceSummaryProvider),
      ),
      data: (value) => ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        itemCount: value.subjects.length,
        separatorBuilder: (_, _) => const SizedBox(height: 8),
        itemBuilder: (context, index) {
          final subject = value.subjects[index];
          final low = subject.percent < 75;
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${subject.subjectCode} · ${subject.subjectName}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  Text('Total: ${subject.total}  Present: ${subject.present}'),
                  const SizedBox(height: 8),
                  LinearProgressIndicator(
                    value: subject.percent / 100,
                    color: low
                        ? const Color(0xFFDC2626)
                        : const Color(0xFF16A34A),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '${subject.percent.toStringAsFixed(1)}%',
                    style: TextStyle(
                      color: low
                          ? const Color(0xFFDC2626)
                          : const Color(0xFF16A34A),
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class LmsScreen extends ConsumerStatefulWidget {
  const LmsScreen({super.key});

  @override
  ConsumerState<LmsScreen> createState() => _LmsScreenState();
}

class _LmsScreenState extends ConsumerState<LmsScreen> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final lms = ref.watch(lmsSubjectsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('LMS')),
      body: lms.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ApiErrorView(
          error: error,
          onRetry: () => ref.invalidate(lmsSubjectsProvider),
        ),
        data: (value) {
          final subjects = value.subjects.where((subject) {
            final haystack =
                '${subject.subjectCode} ${subject.altCode ?? ''} '
                        '${subject.subjectName}'
                    .toLowerCase();
            return haystack.contains(_query.toLowerCase());
          }).toList();
          return Column(
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(16, 16, 16, 8),
                child: DemoDataBanner(),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                child: TextField(
                  key: const Key('lms_search'),
                  decoration: const InputDecoration(
                    labelText: 'Search subjects',
                    prefixIcon: Icon(Icons.search),
                  ),
                  onChanged: (value) => setState(() => _query = value),
                ),
              ),
              Expanded(
                child: subjects.isEmpty
                    ? const Center(child: Text('No subjects found.'))
                    : ListView.separated(
                        padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                        itemCount: subjects.length,
                        separatorBuilder: (_, _) => const SizedBox(height: 8),
                        itemBuilder: (context, index) {
                          final subject = subjects[index];
                          return Card(
                            child: ListTile(
                              title: Text(
                                '${subject.subjectCode} · ${subject.subjectName}',
                              ),
                              subtitle: Text(subject.facultyNames.join(', ')),
                              onTap: () => showModalBottomSheet<void>(
                                context: context,
                                builder: (_) => Padding(
                                  padding: const EdgeInsets.all(20),
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        subject.subjectName,
                                        style: Theme.of(context)
                                            .textTheme
                                            .titleLarge,
                                      ),
                                      const SizedBox(height: 8),
                                      Text('Code: ${subject.subjectCode}'),
                                      if (subject.altCode != null)
                                        Text(
                                          'ERP alternative: ${subject.altCode}',
                                        ),
                                      Text('Component: ${subject.component}'),
                                      Text('Semester: ${subject.semester}'),
                                      Text(
                                        'Faculty: ${subject.facultyNames.join(', ')}',
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          );
                        },
                      ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class AcademicCalendarScreen extends ConsumerWidget {
  const AcademicCalendarScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final holidays = ref.watch(academicHolidaysProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Academic Calendar')),
      body: holidays.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ApiErrorView(
          error: error,
          onRetry: () => ref.invalidate(academicHolidaysProvider),
        ),
        data: (items) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const DemoDataBanner(),
            const SizedBox(height: 12),
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text('Term dates not loaded'),
              ),
            ),
            const SizedBox(height: 12),
            if (items.isEmpty)
              const Center(child: Text('No holidays available.'))
            else
              for (final holiday in items)
                Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: const Icon(
                      Icons.event_available,
                      color: Color(0xFF16A34A),
                    ),
                    title: Text(holiday.name),
                    subtitle: Text(holiday.date),
                  ),
                ),
          ],
        ),
      ),
    );
  }
}

class StudentFeesScreen extends ConsumerWidget {
  const StudentFeesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final fees = ref.watch(studentFeesProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Fees')),
      body: fees.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ApiErrorView(
          error: error,
          onRetry: () => ref.invalidate(studentFeesProvider),
        ),
        data: (value) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const DemoDataBanner(),
            const SizedBox(height: 12),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
              childAspectRatio: 1.7,
              children: [
                _FeeSummaryCard(
                  title: 'To Be Collected',
                  value: value.ledger.toBeCollected,
                ),
                _FeeSummaryCard(title: 'Paid', value: value.ledger.paid),
                _FeeSummaryCard(
                  title: 'Previous',
                  value: value.ledger.previous,
                ),
                _FeeSummaryCard(title: 'Pending', value: value.ledger.pending),
              ],
            ),
            const SizedBox(height: 12),
            for (final year in value.years)
              Card(
                child: ExpansionTile(
                  title: Text('Year ${year.year}'),
                  subtitle: Text('₹${year.total}'),
                  children: [
                    for (final receipt in year.receipts)
                      ListTile(
                        title: Text(receipt.receiptNo),
                        subtitle: Text('${receipt.date} · ${receipt.mode}'),
                        trailing: Text(
                          '₹${receipt.heads.fold<int>(0, (sum, head) => sum + head.amount)}',
                        ),
                      ),
                  ],
                ),
              ),
            const SizedBox(height: 12),
            SectionCard(
              title: 'Scholarship',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(value.scholarship.status),
                  Text(value.scholarship.note),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FeeSummaryCard extends StatelessWidget {
  const _FeeSummaryCard({required this.title, required this.value});
  final String title;
  final int value;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(title, style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 4),
          Text(
            '₹$value',
            style: Theme.of(context).textTheme.titleMedium
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
        ],
      ),
    ),
  );
}
