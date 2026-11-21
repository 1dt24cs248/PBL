import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/widgets/api_error_view.dart';
import '../timetable/campus_repository.dart';

class RoomAvailabilityScreen extends ConsumerStatefulWidget {
  const RoomAvailabilityScreen({super.key});

  @override
  ConsumerState<RoomAvailabilityScreen> createState() =>
      _RoomAvailabilityScreenState();
}

class _RoomAvailabilityScreenState
    extends ConsumerState<RoomAvailabilityScreen> {
  final _capacityController = TextEditingController(text: '0');
  String _day = 'Mon';
  int _period = 1;
  int _minimumCapacity = 0;

  static const _days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  @override
  void dispose() {
    _capacityController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final query = (day: _day, period: _period);
    final rooms = ref.watch(roomAvailabilityProvider(query));
    return Scaffold(
      appBar: AppBar(title: const Text('Room Availability Finder')),
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
                    const SizedBox(width: 12),
                    Expanded(
                      child: DropdownButtonFormField<int>(
                        initialValue: _period,
                        decoration: const InputDecoration(labelText: 'Period'),
                        items: [
                          for (var period = 1; period <= 7; period++)
                            DropdownMenuItem(
                              value: period,
                              child: Text('$period'),
                            ),
                        ],
                        onChanged: (value) {
                          if (value != null) setState(() => _period = value);
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                TextField(
                  key: const Key('minimum_capacity_field'),
                  controller: _capacityController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Minimum capacity',
                    suffixText: 'people',
                  ),
                  onChanged: (value) {
                    final capacity = int.tryParse(value);
                    if (capacity != null && capacity >= 0) {
                      setState(() => _minimumCapacity = capacity);
                    }
                  },
                ),
              ],
            ),
          ),
          Expanded(
            child: rooms.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => ApiErrorView(
                error: error,
                onRetry: () => ref.invalidate(roomAvailabilityProvider(query)),
              ),
              data: (availableRooms) {
                final filteredRooms =
                    availableRooms
                        .where(
                          (room) => room.capacity == null
                              ? _minimumCapacity == 0
                              : room.capacity! >= _minimumCapacity,
                        )
                        .toList()
                      ..sort((a, b) => a.number.compareTo(b.number));
                if (filteredRooms.isEmpty) {
                  return const Center(
                    child: Text('No free rooms match these filters.'),
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: filteredRooms.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final room = filteredRooms[index];
                    final statusLabel = switch (room.dataStatus) {
                      'SYNTHETIC' => 'Synthetic',
                      'INFERRED' => 'Inferred',
                      _ => null,
                    };
                    final floor = room.floor == null
                        ? 'Floor unavailable'
                        : room.floorName == null
                        ? 'Floor ${room.floor}'
                        : 'Floor ${room.floor} · ${room.floorName}';
                    final capacity = room.capacity == null
                        ? 'Capacity unavailable'
                        : 'Capacity ${room.capacity}';
                    return Card(
                      child: ListTile(
                        title: Text(room.number),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (room.realLabel != null) Text(room.realLabel!),
                            Text('$floor · $capacity'),
                          ],
                        ),
                        trailing: statusLabel == null
                            ? const Icon(Icons.check_circle_outline)
                            : Chip(
                                label: Text(statusLabel),
                                visualDensity: VisualDensity.compact,
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
}
