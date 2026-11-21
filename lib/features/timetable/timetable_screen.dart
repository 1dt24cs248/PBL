import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/widgets/api_error_view.dart';
import 'campus_repository.dart';

class TimetableScreen extends ConsumerStatefulWidget {
  const TimetableScreen({super.key, this.initialDate});

  final DateTime? initialDate;

  @override
  ConsumerState<TimetableScreen> createState() => _TimetableScreenState();
}

class _TimetableScreenState extends ConsumerState<TimetableScreen> {
  String _week = 'All weeks';
  String _day = 'All';
  late DateTime? _date = widget.initialDate;

  static const _days = ['All', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  @override
  Widget build(BuildContext context) {
    final timetable = ref.watch(studentTimetableProvider);
    final dateText = _date == null ? null : _formatDate(_date!);
    final dateResult = dateText == null
        ? null
        : ref.watch(timetableDateProvider(dateText));
    return Scaffold(
      appBar: AppBar(title: const Text('Student Timetable')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Row(
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
                              (day) => DropdownMenuItem(
                                value: day,
                                child: Text(day),
                              ),
                            )
                            .toList(),
                        onChanged: (value) {
                          if (value != null) setState(() => _day = value);
                        },
                      ),
                    ),
                  ],
                ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    key: const Key('choose_timetable_date'),
                    onPressed: _chooseDate,
                    icon: const Icon(Icons.calendar_today_outlined),
                    label: Text(dateText ?? 'Check a date or holiday'),
                  ),
                ),
                if (dateResult != null)
                  dateResult.when(
                    loading: () => const LinearProgressIndicator(),
                    error: (error, _) => ApiErrorView(
                      error: error,
                      onRetry: () =>
                          ref.invalidate(timetableDateProvider(dateText!)),
                    ),
                    data: (result) {
                      final holiday = result.holiday;
                      if (holiday == null || holiday.isEmpty) {
                        return Text('${result.weekday} · No holiday');
                      }
                      return Card(
                        key: const Key('holiday_banner'),
                        color: Theme.of(context).colorScheme.tertiaryContainer,
                        child: ListTile(
                          leading: const Icon(Icons.event_available_outlined),
                          title: Text(_holidayName(holiday)),
                          subtitle: const Text('Holiday'),
                        ),
                      );
                    },
                  ),
              ],
            ),
          ),
          Expanded(
            child: timetable.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => ApiErrorView(
                error: error,
                onRetry: () => ref.invalidate(studentTimetableProvider),
              ),
              data: (data) {
                final sessions =
                    data.sessions
                        .where(
                          (session) => _day == 'All' || session.day == _day,
                        )
                        .toList()
                      ..sort((a, b) {
                        final dayOrder = a.day.compareTo(b.day);
                        if (dayOrder != 0) return dayOrder;
                        return (a.periods.isEmpty ? 0 : a.periods.first)
                            .compareTo(b.periods.isEmpty ? 0 : b.periods.first);
                      });
                if (sessions.isEmpty) {
                  return const Center(
                    child: Text('No timetable sessions for this selection.'),
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  itemCount: sessions.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, index) =>
                      _TimetableSessionCard(session: sessions[index]),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _chooseDate() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _date ?? DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime(2035),
    );
    if (date != null) setState(() => _date = date);
  }

  String _formatDate(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';

  String _holidayName(String holiday) =>
      holiday.replaceFirst(RegExp(r'\s+\d{4}$'), '');
}

class FacultyTimetableScreen extends ConsumerStatefulWidget {
  const FacultyTimetableScreen({super.key});

  @override
  ConsumerState<FacultyTimetableScreen> createState() =>
      _FacultyTimetableScreenState();
}

class _FacultyTimetableScreenState
    extends ConsumerState<FacultyTimetableScreen> {
  String? _day;

  static const _days = ['All', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  @override
  Widget build(BuildContext context) {
    final timetable = ref.watch(facultyTimetableProvider(_day));
    return Scaffold(
      appBar: AppBar(title: const Text('Faculty Timetable')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: DropdownButtonFormField<String>(
              initialValue: _day ?? 'All',
              decoration: const InputDecoration(labelText: 'Day'),
              items: _days
                  .map((day) => DropdownMenuItem(value: day, child: Text(day)))
                  .toList(),
              onChanged: (value) =>
                  setState(() => _day = value == 'All' ? null : value),
            ),
          ),
          Expanded(
            child: timetable.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) {
                final failure = TimetableFailure.from(error);
                return ApiErrorView(
                  error: error,
                  notFoundMessage: failure.statusCode == 404
                      ? 'Faculty timetable is unavailable for this account.'
                      : null,
                  onRetry: () => ref.invalidate(facultyTimetableProvider(_day)),
                );
              },
              data: (data) {
                final sessions =
                    data.sessions
                        .where((session) => _day == null || session.day == _day)
                        .toList()
                      ..sort((a, b) {
                        final dayOrder = a.day.compareTo(b.day);
                        if (dayOrder != 0) return dayOrder;
                        return (a.periods.isEmpty ? 0 : a.periods.first)
                            .compareTo(b.periods.isEmpty ? 0 : b.periods.first);
                      });
                if (sessions.isEmpty) {
                  return const Center(
                    child: Text('No faculty timetable sessions for this day.'),
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: sessions.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, index) =>
                      _TimetableSessionCard(session: sessions[index]),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _TimetableSessionCard extends StatelessWidget {
  const _TimetableSessionCard({required this.session});

  final TimetableSession session;

  @override
  Widget build(BuildContext context) {
    final provenanceBadge = switch (session.provenance) {
      'INFERRED' => 'Inferred',
      'SYNTHETIC' => 'Synthetic',
      _ => null,
    };
    final subjectName = session.subjectName;
    final facultyName = session.facultyName;
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
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                if (provenanceBadge != null)
                  Chip(
                    label: Text(provenanceBadge),
                    visualDensity: VisualDensity.compact,
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              subjectName == null || subjectName.isEmpty
                  ? session.subjectCode
                  : '${session.subjectCode} · $subjectName',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (session.sectionCode != null)
              Text('Section: ${session.sectionCode}'),
            if (session.facultyInitials != null || facultyName != null)
              Text('Faculty: ${facultyName ?? session.facultyInitials ?? '-'}'),
            Text('Room: ${session.roomId ?? '-'}'),
          ],
        ),
      ),
    );
  }
}

String _periodText(List<int> periods) {
  if (periods.isEmpty) return 'Period';
  if (periods.length == 1) return 'Period ${periods.first}';
  return 'Periods ${periods.join('-')}';
}
