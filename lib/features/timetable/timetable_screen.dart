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
  late DateTime _date;
  late DateTime _weekStart;

  @override
  void initState() {
    super.initState();
    _date = widget.initialDate ?? DateTime.now();
    _weekStart = _startOfWeek(_date);
  }

  static const _weekdayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  @override
  Widget build(BuildContext context) {
    final timetable = ref.watch(studentTimetableProvider);
    final dateText = _formatDate(_date);
    final dateResult = ref.watch(timetableDateProvider(dateText));
    return Scaffold(
      appBar: AppBar(
        title: const Text('Student Timetable'),
        actions: [
          IconButton(
            key: const Key('choose_timetable_date'),
            tooltip: 'Choose date',
            onPressed: _chooseDate,
            icon: const Icon(Icons.calendar_today_outlined),
          ),
        ],
      ),
      body: Column(
        children: [
          _WeekStrip(
            weekStart: _weekStart,
            selectedDate: _date,
            onPrevious: () => setState(() {
              _weekStart = _weekStart.subtract(const Duration(days: 7));
              _date = _weekStart;
            }),
            onNext: () => setState(() {
              _weekStart = _weekStart.add(const Duration(days: 7));
              _date = _weekStart;
            }),
            onSelect: (date) => setState(() => _date = date),
          ),
          dateResult.when(
            loading: () => const LinearProgressIndicator(),
            error: (error, _) => ApiErrorView(
              error: error,
              onRetry: () => ref.invalidate(timetableDateProvider(dateText)),
            ),
            data: (result) {
              if (result.holiday == null || result.holiday!.isEmpty) {
                return const SizedBox.shrink();
              }
              return Card(
                key: const Key('holiday_banner'),
                margin: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                color: const Color(0xFF1ABC9C),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 18),
                  child: Column(
                    children: [
                      const Text(
                        'Holiday',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        result.holiday!,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
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
                          (session) =>
                              session.day == _weekdayNames[_date.weekday - 1],
                        )
                        .toList()
                      ..sort((a, b) {
                        final dayOrder = a.day.compareTo(b.day);
                        if (dayOrder != 0) return dayOrder;
                        return (a.periods.isEmpty ? 0 : a.periods.first)
                            .compareTo(b.periods.isEmpty ? 0 : b.periods.first);
                      });
                final holiday = dateResult.value?.holiday;
                if (holiday != null && holiday.isNotEmpty) {
                  return const Center(child: Text('No sessions on holiday.'));
                }
                if (sessions.isEmpty) {
                  return const Center(
                    child: Text('No timetable sessions for this selection.'),
                  );
                }
                final merged = _mergeSessions(sessions);
                return ListView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  itemCount: _itemsWithRecess(merged).length,
                  itemBuilder: (context, index) {
                    final item = _itemsWithRecess(merged)[index];
                    if (item is _RecessItem) {
                      return _RecessBanner(afterPeriod: item.afterPeriod);
                    }
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: _TimetableSessionCard(
                        session: (item as _MergedSession).session,
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

  Future<void> _chooseDate() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2026, 6, 1),
      lastDate: DateTime(2027, 6, 30),
    );
    if (date != null) {
      setState(() {
        _date = date;
        _weekStart = _startOfWeek(date);
      });
    }
  }

  String _formatDate(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';
}

DateTime _startOfWeek(DateTime date) => DateTime(
  date.year,
  date.month,
  date.day,
).subtract(Duration(days: date.weekday - 1));

class _WeekStrip extends StatelessWidget {
  const _WeekStrip({
    required this.weekStart,
    required this.selectedDate,
    required this.onPrevious,
    required this.onNext,
    required this.onSelect,
  });

  final DateTime weekStart;
  final DateTime selectedDate;
  final VoidCallback onPrevious;
  final VoidCallback onNext;
  final ValueChanged<DateTime> onSelect;

  @override
  Widget build(BuildContext context) => Container(
    color: Colors.white,
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
    child: Row(
      children: [
        IconButton(
          key: const Key('previous_week'),
          onPressed: onPrevious,
          icon: const Icon(Icons.chevron_left),
        ),
        Expanded(
          child: Row(
            children: [
              for (var index = 0; index < 6; index++)
                Expanded(
                  child: _WeekDayButton(
                    date: weekStart.add(Duration(days: index)),
                    selected:
                        selectedDate.year == weekStart.year &&
                        selectedDate.month == weekStart.month &&
                        selectedDate.day ==
                            weekStart.add(Duration(days: index)).day,
                    onTap: onSelect,
                  ),
                ),
            ],
          ),
        ),
        IconButton(
          key: const Key('next_week'),
          onPressed: onNext,
          icon: const Icon(Icons.chevron_right),
        ),
      ],
    ),
  );
}

class _WeekDayButton extends StatelessWidget {
  const _WeekDayButton({
    required this.date,
    required this.selected,
    required this.onTap,
  });

  final DateTime date;
  final bool selected;
  final ValueChanged<DateTime> onTap;

  @override
  Widget build(BuildContext context) {
    const names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    final name = names[date.weekday - 1];
    return InkWell(
      onTap: () => onTap(date),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 2),
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: selected ? const Color(0xFF111827) : Colors.transparent,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '${date.day}',
              style: TextStyle(
                color: selected ? Colors.white : const Color(0xFF111827),
                fontWeight: FontWeight.w800,
              ),
            ),
            Text(
              name,
              style: TextStyle(
                color: selected ? Colors.white70 : const Color(0xFF64748B),
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MergedSession {
  const _MergedSession(this.session);
  final TimetableSession session;
}

class _RecessItem {
  const _RecessItem({required this.afterPeriod});
  final int afterPeriod;
}

List<TimetableSession> _mergeSessions(List<TimetableSession> sessions) {
  final merged = <TimetableSession>[];
  for (final session in sessions) {
    if (session.blockId != null) {
      final index = merged.indexWhere(
        (item) => item.blockId == session.blockId,
      );
      if (index >= 0) continue;
    }
    merged.add(session);
  }
  return merged;
}

List<Object> _itemsWithRecess(List<TimetableSession> sessions) {
  final items = <Object>[];
  for (final session in sessions) {
    final first = session.periods.isEmpty ? null : session.periods.first;
    if (first == 3) {
      items.add(const _RecessItem(afterPeriod: 2));
    }
    if (first == 5) {
      items.add(const _RecessItem(afterPeriod: 4));
    }
    items.add(_MergedSession(session));
  }
  return items;
}

class _RecessBanner extends StatelessWidget {
  const _RecessBanner({this.afterPeriod = 2});
  final int afterPeriod;

  @override
  Widget build(BuildContext context) => Container(
    key: const Key('recess_banner'),
    width: double.infinity,
    margin: const EdgeInsets.only(bottom: 8),
    padding: const EdgeInsets.symmetric(vertical: 8),
    color: const Color(0xFFFBF8D2),
    child: Column(
      children: [
        const Text(
          'RECESS',
          style: TextStyle(
            color: Color(0xFFE6B800),
            fontWeight: FontWeight.w800,
          ),
        ),
        Text(
          afterPeriod == 2 ? 'Tea 11:20-11:35' : 'Lunch 13:25-14:15',
          style: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
        ),
      ],
    ),
  );
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
    final subjectName = session.subjectName;
    final facultyName = session.facultyNames.isNotEmpty
        ? session.facultyNames.join(', ')
        : session.facultyName;
    final type = session.sessionType;
    final typeColors = switch (type) {
      'Lab' => (const Color(0xFFFBD5DC), const Color(0xFFD6336C)),
      'Activity' => (const Color(0xFFE5E7EB), const Color(0xFF4B5563)),
      _ => (const Color(0xFFD9F3F5), const Color(0xFF0F8A94)),
    };
    final timeLabel = session.startTime != null && session.endTime != null
        ? '${_formatTime(session.startTime!)} to ${_formatTime(session.endTime!)}'
        : _periodText(session.periods);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 112,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (type != null)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: typeColors.$1,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Text(
                        type,
                        style: TextStyle(
                          color: typeColors.$2,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  const SizedBox(height: 8),
                  Text(
                    timeLabel,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    subjectName == null || subjectName.isEmpty
                        ? session.subjectCode
                        : '${session.subjectCode} · $subjectName',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  if (session.sectionCode != null)
                    Text('Section: ${session.sectionCode}'),
                  if (facultyName != null && facultyName.isNotEmpty)
                    Text(facultyName),
                  if (session.roomRequired == true &&
                      session.roomId != null &&
                      session.roomRealLabel != null)
                    Wrap(
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: 6,
                      children: [
                        Text(
                          'Room ${session.roomRealLabel} (${session.roomId})',
                        ),
                        if (session.roomInferred == true)
                          const Chip(
                            key: Key('inferred_room_badge'),
                            label: Text('Inferred'),
                            visualDensity: VisualDensity.compact,
                          ),
                      ],
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

String _periodText(List<int> periods) {
  if (periods.isEmpty) return 'Period';
  if (periods.length == 1) return 'Period ${periods.first}';
  return 'Periods ${periods.join('-')}';
}

String _formatTime(String hhmm) {
  final parts = hhmm.split(':');
  if (parts.length != 2) return hhmm;
  final hour = int.tryParse(parts[0]);
  final minute = int.tryParse(parts[1]);
  if (hour == null || minute == null) return hhmm;
  final suffix = hour >= 12 ? 'PM' : 'AM';
  final displayHour = hour == 0 ? 12 : (hour > 12 ? hour - 12 : hour);
  return '$displayHour:${minute.toString().padLeft(2, '0')} $suffix';
}
