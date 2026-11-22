import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../shared/widgets/api_error_view.dart';
import '../../features/authentication/authentication_screen.dart';
import '../energy/energy_repository.dart';
import 'campus_map_models.dart';
import 'campus_map_painters.dart';
import 'campus_map_repository.dart';

class CampusMapScreen extends ConsumerStatefulWidget {
  const CampusMapScreen({super.key});

  @override
  ConsumerState<CampusMapScreen> createState() => _CampusMapScreenState();
}

class _CampusMapScreenState extends ConsumerState<CampusMapScreen> {
  bool _isometric = false;
  bool _reduceEffects = false;
  bool _energyOverlay = false;

  @override
  Widget build(BuildContext context) {
    final floorIndex = ref.watch(campusFloorIndexProvider);
    final selection = ref.watch(campusMapSelectionProvider);
    final role = ref.watch(authProvider).value?.role;
    final canViewEnergy = role == 'admin' || role == 'hod';
    final baseline = _energyOverlay && canViewEnergy
        ? ref.watch(energyBaselineProvider)
        : null;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Campus Map'),
        actions: [
          IconButton(
            key: const Key('open_route_navigator'),
            tooltip: 'Route Navigator',
            onPressed: () => context.go('/route-navigator'),
            icon: const Icon(Icons.alt_route),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Schematic layout (synthetic)',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          if (_energyOverlay)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text('Modelled on synthetic wattage and tariff'),
            ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 12,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Switch(
                key: const Key('campus_25d_toggle'),
                value: _isometric,
                onChanged: (value) => setState(() => _isometric = value),
              ),
              const Text('2.5D view'),
              if (_isometric)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Switch(
                      key: const Key('reduce_effects_toggle'),
                      value: _reduceEffects,
                      onChanged: (value) =>
                          setState(() => _reduceEffects = value),
                    ),
                    const Text('Reduce effects'),
                  ],
                ),
              if (_isometric && canViewEnergy)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Switch(
                      key: const Key('energy_overlay_toggle'),
                      value: _energyOverlay,
                      onChanged: (value) =>
                          setState(() => _energyOverlay = value),
                    ),
                    const Text('Energy overlay'),
                  ],
                ),
            ],
          ),
          const SizedBox(height: 8),
          floorIndex.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => ApiErrorView(
              error: error,
              onRetry: () => ref.invalidate(campusFloorIndexProvider),
            ),
            data: (index) {
              final query = (
                floor: selection.floor,
                day: selection.day,
                period: selection.period,
                date: null,
              );
              final floorPlan = ref.watch(campusFloorPlanProvider(query));
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 12,
                    runSpacing: 8,
                    children: [
                      DropdownButton<int>(
                        key: const Key('floor_selector'),
                        value: selection.floor,
                        underline: const SizedBox.shrink(),
                        items: [
                          for (final floor in index.floors)
                            DropdownMenuItem(
                              value: floor.floor,
                              child: Text('${floor.label} (${floor.floor})'),
                            ),
                        ],
                        onChanged: (floor) {
                          if (floor != null) {
                            ref
                                .read(campusMapSelectionProvider.notifier)
                                .selectFloor(floor);
                          }
                        },
                      ),
                      DropdownButton<String>(
                        key: const Key('map_day_selector'),
                        value: selection.day,
                        underline: const SizedBox.shrink(),
                        items: [
                          for (final day in [
                            'Mon',
                            'Tue',
                            'Wed',
                            'Thu',
                            'Fri',
                            'Sat',
                          ])
                            DropdownMenuItem(value: day, child: Text(day)),
                        ],
                        onChanged: (day) {
                          if (day != null) {
                            ref
                                .read(campusMapSelectionProvider.notifier)
                                .selectDay(day);
                          }
                        },
                      ),
                      DropdownButton<int>(
                        key: const Key('map_period_selector'),
                        value: selection.period,
                        underline: const SizedBox.shrink(),
                        items: [
                          for (var period = 1; period <= 8; period++)
                            DropdownMenuItem(
                              value: period,
                              child: Text('Period $period'),
                            ),
                        ],
                        onChanged: (period) {
                          if (period != null) {
                            ref
                                .read(campusMapSelectionProvider.notifier)
                                .selectPeriod(period);
                          }
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  _CampusMapLegend(),
                  const SizedBox(height: 8),
                  floorPlan.when(
                    loading: () =>
                        const Center(child: CircularProgressIndicator()),
                    error: (error, _) => ApiErrorView(
                      error: error,
                      notFoundMessage: 'The selected floor was not found.',
                      onRetry: () =>
                          ref.invalidate(campusFloorPlanProvider(query)),
                    ),
                    data: (plan) => Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(plan.label),
                        if (plan.holiday != null)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                            child: Text('Holiday: ${plan.holiday}'),
                          ),
                        const SizedBox(height: 8),
                        if (_isometric)
                          CampusIsometricMapView(
                            plan: plan,
                            energyByRoom: baseline?.value == null
                                ? const {}
                                : {
                                    for (final room
                                        in baseline!
                                            .value!
                                            .timetableOccupancy
                                            .rooms)
                                      room.roomId: room.kwhWeek ?? 0,
                                  },
                            onRoomTap: (room) =>
                                _showRoomDetail(context, plan, room, selection),
                          )
                        else
                          CampusFloorMapView(
                            plan: plan,
                            onRoomTap: (room) =>
                                _showRoomDetail(context, plan, room, selection),
                          ),
                        const SizedBox(height: 12),
                        const Text(
                          'Tap a room for its occupancy and provenance details. '
                          'Pinch to zoom and drag to pan.',
                        ),
                      ],
                    ),
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  void _showRoomDetail(
    BuildContext context,
    CampusFloorPlan plan,
    CampusFloorRoom room,
    dynamic selection,
  ) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => CampusRoomDetailSheet(
        room: room,
        floor: plan.floor,
        weekday: plan.weekday ?? selection.day,
        period: selection.period,
      ),
    );
  }
}

class _CampusMapLegend extends StatelessWidget {
  @override
  Widget build(BuildContext context) => const Wrap(
    spacing: 12,
    runSpacing: 4,
    children: [
      _MapLegendItem(color: Color(0xFF15803D), label: 'Available'),
      _MapLegendItem(color: Color(0xFFEA580C), label: 'Occupied now'),
      _MapLegendItem(color: Color(0xFFB91C1C), label: 'Under maintenance'),
      _MapLegendItem(
        color: Color(0xFF64748B),
        label: 'Temporarily unavailable',
      ),
    ],
  );
}

class _MapLegendItem extends StatelessWidget {
  const _MapLegendItem({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(width: 12, height: 12, color: color),
      const SizedBox(width: 4),
      Text(label),
    ],
  );
}

class CampusRoomDetailSheet extends StatelessWidget {
  const CampusRoomDetailSheet({
    super.key,
    required this.room,
    required this.floor,
    required this.weekday,
    required this.period,
  });

  final CampusFloorRoom room;
  final int floor;
  final String weekday;
  final int period;

  @override
  Widget build(BuildContext context) {
    final occupancy = room.occupancy;
    final capacityLabel = switch (room.dataStatus) {
      'SYNTHETIC' => 'Synthetic capacity',
      'INFERRED' => 'Inferred capacity',
      'REAL_DSATM_PDF' => 'Real DSATM capacity',
      _ => null,
    };
    final statusLabel = switch (room.status) {
      'under_maintenance' => 'Under maintenance',
      'temporarily_unavailable' => 'Temporarily unavailable',
      _ => room.status,
    };

    return SafeArea(
      child: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(
          20,
          20,
          20,
          MediaQuery.viewInsetsOf(context).bottom + 20,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(room.roomId, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(room.realLabel),
            const SizedBox(height: 12),
            Row(
              children: [
                Text('Capacity: ${room.capacityEffective}'),
                if (capacityLabel != null) ...[
                  const SizedBox(width: 8),
                  Chip(
                    key: const Key('room_capacity_provenance'),
                    label: Text(capacityLabel),
                    visualDensity: VisualDensity.compact,
                  ),
                ],
              ],
            ),
            Text('Floor: $floor'),
            Text('Status: $statusLabel'),
            Text('Data status: ${room.dataStatus}'),
            const Divider(height: 24),
            Text(
              'Occupancy · $weekday, period $period',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (occupancy == null)
              const Text('No occupancy data was returned for this selection.')
            else ...[
              Text('Occupied now: ${occupancy.occupied ? 'Yes' : 'No'}'),
              Text('Sessions: ${occupancy.sessions.length}'),
            ],
          ],
        ),
      ),
    );
  }
}

class RouteNavigatorScreen extends ConsumerStatefulWidget {
  const RouteNavigatorScreen({super.key});

  @override
  ConsumerState<RouteNavigatorScreen> createState() =>
      _RouteNavigatorScreenState();
}

class _RouteNavigatorScreenState extends ConsumerState<RouteNavigatorScreen> {
  CampusRoomRecord? _fromRoom;
  CampusRoomRecord? _toRoom;
  String _mode = 'stairs';

  Future<void> _findRoute() async {
    final from = _fromRoom;
    final to = _toRoom;
    if (from == null || to == null) return;
    await ref
        .read(campusRouteProvider.notifier)
        .findRoute(from: from.number, to: to.number, mode: _mode);
  }

  void _selectFrom(CampusRoomRecord? room) {
    setState(() => _fromRoom = room);
    ref.invalidate(campusRouteProvider);
  }

  void _selectTo(CampusRoomRecord? room) {
    setState(() => _toRoom = room);
    ref.invalidate(campusRouteProvider);
  }

  @override
  Widget build(BuildContext context) {
    final rooms = ref.watch(campusRoomsProvider);
    final route = ref.watch(campusRouteProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Route Navigator')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          rooms.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => ApiErrorView(
              error: error,
              onRetry: () => ref.invalidate(campusRoomsProvider),
            ),
            data: (items) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _CampusRoomAutocomplete(
                  key: const Key('from_room_autocomplete'),
                  fieldKey: const Key('from_room_field'),
                  label: 'From',
                  rooms: items,
                  selectedRoom: _fromRoom,
                  onSelected: _selectFrom,
                ),
                const SizedBox(height: 12),
                _CampusRoomAutocomplete(
                  key: const Key('to_room_autocomplete'),
                  fieldKey: const Key('to_room_field'),
                  label: 'To',
                  rooms: items,
                  selectedRoom: _toRoom,
                  onSelected: _selectTo,
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  key: const Key('route_mode_selector'),
                  initialValue: _mode,
                  decoration: const InputDecoration(labelText: 'Mode'),
                  items: const [
                    DropdownMenuItem(value: 'stairs', child: Text('Stairs')),
                    DropdownMenuItem(value: 'lift', child: Text('Lift')),
                    DropdownMenuItem(
                      value: 'accessible',
                      child: Text('Accessible'),
                    ),
                  ],
                  onChanged: (mode) {
                    if (mode != null) {
                      setState(() => _mode = mode);
                      ref.invalidate(campusRouteProvider);
                    }
                  },
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  key: const Key('find_route_button'),
                  onPressed: _fromRoom == null || _toRoom == null
                      ? null
                      : _findRoute,
                  icon: const Icon(Icons.directions),
                  label: const Text('Find route'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          route.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => ApiErrorView(
              error: error,
              notFoundMessage:
                  'Unknown room. Select a room code, real label, or alias.',
              onRetry: _findRoute,
            ),
            data: (result) => result == null
                ? const SizedBox.shrink()
                : _RouteResultView(route: result),
          ),
        ],
      ),
    );
  }
}

class _CampusRoomAutocomplete extends StatelessWidget {
  const _CampusRoomAutocomplete({
    super.key,
    required this.fieldKey,
    required this.label,
    required this.rooms,
    required this.selectedRoom,
    required this.onSelected,
  });

  final Key fieldKey;
  final String label;
  final List<CampusRoomRecord> rooms;
  final CampusRoomRecord? selectedRoom;
  final ValueChanged<CampusRoomRecord?> onSelected;

  @override
  Widget build(BuildContext context) => Autocomplete<CampusRoomRecord>(
    displayStringForOption: (room) => '${room.number} · ${room.realLabel}',
    optionsBuilder: (value) => rooms.where((room) => room.matches(value.text)),
    onSelected: onSelected,
    fieldViewBuilder: (context, controller, focusNode, onFieldSubmitted) =>
        TextFormField(
          key: fieldKey,
          controller: controller,
          focusNode: focusNode,
          decoration: InputDecoration(
            labelText: label,
            hintText: 'Search room code, real label, or alias',
          ),
          onChanged: (value) {
            final current = selectedRoom;
            if (current != null &&
                value != '${current.number} · ${current.realLabel}') {
              onSelected(null);
            }
          },
          onFieldSubmitted: (_) => onFieldSubmitted(),
        ),
    optionsViewBuilder: (context, onSelectedOption, options) => Align(
      alignment: Alignment.topLeft,
      child: Material(
        elevation: 4,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 260),
          child: ListView(
            padding: EdgeInsets.zero,
            shrinkWrap: true,
            children: [
              for (final room in options)
                ListTile(
                  title: Text(room.number),
                  subtitle: Text(
                    room.aliases.isEmpty
                        ? room.realLabel
                        : '${room.realLabel} · ${room.aliases.join(', ')}',
                  ),
                  onTap: () => onSelectedOption(room),
                ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _RouteResultView extends StatelessWidget {
  const _RouteResultView({required this.route});

  final CampusRoute route;

  @override
  Widget build(BuildContext context) {
    final floors = route.floorsVisited;
    final summary = route.summary;
    final timeLabel = summary == null
        ? '${(route.routeCostSeconds / 60).ceil()} min'
        : '${summary.estMinutes} min';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Card(
          key: const Key('route_summary_card'),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  summary == null
                      ? '${route.fromRoom} → ${route.toRoom}'
                      : '${summary.start.realLabel} (${summary.start.code}) → '
                            '${summary.end.realLabel} (${summary.end.code})',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 16,
                  runSpacing: 8,
                  children: [
                    Text(
                      'Distance: ${summary?.distanceMetres.toStringAsFixed(1) ?? route.distanceMetres.toStringAsFixed(1)} m',
                    ),
                    Text('Estimated time: $timeLabel'),
                    Chip(label: Text(summary?.mode ?? route.mode)),
                    if (summary != null)
                      Text('Floors: ${summary.floorsTraversed.join(', ')}'),
                  ],
                ),
              ],
            ),
          ),
        ),
        if (floors.isNotEmpty)
          DefaultTabController(
            key: ValueKey('${route.nodeKeys.join('|')}:${floors.join(',')}'),
            length: floors.length,
            child: Column(
              children: [
                TabBar(
                  isScrollable: true,
                  tabs: [for (final floor in floors) Tab(text: 'Floor $floor')],
                ),
                SizedBox(
                  height: 220,
                  child: TabBarView(
                    children: [
                      for (final floor in floors)
                        CampusRouteFloorMap(route: route, floor: floor),
                    ],
                  ),
                ),
              ],
            ),
          ),
        const SizedBox(height: 12),
        Text('Route steps', style: Theme.of(context).textTheme.titleMedium),
        if (route.instructions.isNotEmpty)
          for (final instruction in route.instructions)
            ListTile(
              key: Key('route_instruction_${instruction.index}'),
              contentPadding: EdgeInsets.zero,
              leading: CircleAvatar(
                child: Icon(switch (instruction.kind) {
                  'start' => Icons.trip_origin,
                  'walk' => Icons.directions_walk,
                  'stairs' => Icons.stairs,
                  'lift' => Icons.elevator,
                  'arrive' => Icons.location_on,
                  _ => Icons.route,
                }),
              ),
              title: Text(instruction.text),
              subtitle: instruction.distanceMetres > 0
                  ? Text('${instruction.distanceMetres.toStringAsFixed(1)} m')
                  : null,
            )
        else if (route.steps.isEmpty)
          const Text('This route has no walking or floor-transition steps.')
        else
          for (final (index, step) in route.steps.indexed)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: CircleAvatar(child: Text('${index + 1}')),
              title: Text(step.instruction),
              subtitle: Text(
                'Floor ${step.floor} · ${step.kind} · '
                '${step.distanceMetres.toStringAsFixed(1)} m',
              ),
            ),
        const SizedBox(height: 8),
        const Text('Blue marker: start · Green marker: destination'),
      ],
    );
  }
}
