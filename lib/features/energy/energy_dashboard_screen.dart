import 'dart:math' as math;

import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/authentication/authentication_screen.dart';
import 'energy_models.dart';
import 'energy_repository.dart';
import 'energy_widgets.dart';

class EnergyDashboardScreen extends ConsumerWidget {
  const EnergyDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final baseline = ref.watch(energyBaselineProvider);
    final utilization = ref.watch(energyUtilizationProvider);
    final role = ref.watch(authProvider).value?.role;
    final isAdmin = role == 'admin';

    return Scaffold(
      appBar: AppBar(title: const Text('Energy Dashboard')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (isAdmin)
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: () => context.go('/energy/optimizer'),
                  icon: const Icon(Icons.tune),
                  label: const Text('Energy Optimizer'),
                ),
                OutlinedButton.icon(
                  onPressed: () => context.go('/proposals'),
                  icon: const Icon(Icons.fact_check_outlined),
                  label: const Text('Proposals'),
                ),
              ],
            )
          else
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                onPressed: () => context.go('/proposals'),
                icon: const Icon(Icons.fact_check_outlined),
                label: const Text('Proposals'),
              ),
            ),
          const SizedBox(height: 12),
          baseline.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => EnergyErrorView(
              error: error,
              onRetry: () => ref.invalidate(energyBaselineProvider),
            ),
            data: (data) => _BaselineReport(baseline: data),
          ),
          const SizedBox(height: 20),
          utilization.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => EnergyErrorView(
              error: error,
              onRetry: () => ref.invalidate(energyUtilizationProvider),
            ),
            data: (data) => _UtilizationReport(utilization: data),
          ),
        ],
      ),
    );
  }
}

class _BaselineReport extends StatelessWidget {
  const _BaselineReport({required this.baseline});

  final EnergyBaseline baseline;

  @override
  Widget build(BuildContext context) {
    final report = baseline.timetableOccupancy;
    final topRooms = [...report.rooms]
      ..sort((a, b) => (b.kwhWeek ?? 0).compareTo(a.kwhWeek ?? 0));
    final maxFloorUsage = report.floors.fold<double>(
      0,
      (maximum, floor) => math.max(maximum, floor.kwhWeek ?? 0),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Term ${baseline.termCode}'),
        const SizedBox(height: 8),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _EnergyMetricCard(
              label: 'kWh / week',
              value: report.block.kwhWeek.toStringAsFixed(2),
              dataStatus: baseline.dataStatus,
            ),
            _EnergyMetricCard(
              label: 'Rs / week',
              value: report.block.costWeekInr?.toStringAsFixed(2) ?? '—',
              dataStatus: baseline.dataStatus,
            ),
          ],
        ),
        const SizedBox(height: 20),
        Text('Energy by floor', style: Theme.of(context).textTheme.titleMedium),
        if (report.floors.isEmpty)
          const Text('No floor energy data is available.')
        else
          for (final floor in report.floors)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      SizedBox(width: 64, child: Text('Floor ${floor.floor}')),
                      Expanded(
                        child: LinearProgressIndicator(
                          value: maxFloorUsage <= 0
                              ? 0
                              : (floor.kwhWeek ?? 0) / maxFloorUsage,
                          minHeight: 8,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Text('${floor.kwhWeek?.toStringAsFixed(2) ?? '—'} kWh'),
                    ],
                  ),
                  Padding(
                    padding: const EdgeInsets.only(left: 64, top: 2),
                    child: SyntheticEnergyLabel(
                      dataStatus: baseline.dataStatus,
                    ),
                  ),
                ],
              ),
            ),
        const SizedBox(height: 20),
        Text(
          'Top 10 consuming rooms',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        if (topRooms.isEmpty)
          const Text('No room energy data is available.')
        else
          for (final room in topRooms.take(10))
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(room.roomId),
              subtitle: SyntheticEnergyLabel(dataStatus: baseline.dataStatus),
              trailing: Text(
                '${room.kwhWeek?.toStringAsFixed(2) ?? '—'} kWh / week',
              ),
            ),
        Text('Recorded room clashes: ${report.recordedRoomClashes}'),
      ],
    );
  }
}

class _EnergyMetricCard extends StatelessWidget {
  const _EnergyMetricCard({
    required this.label,
    required this.value,
    required this.dataStatus,
  });

  final String label;
  final String value;
  final String dataStatus;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 220,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label),
            Text(value, style: Theme.of(context).textTheme.headlineSmall),
            SyntheticEnergyLabel(dataStatus: dataStatus),
          ],
        ),
      ),
    ),
  );
}

class _UtilizationReport extends StatelessWidget {
  const _UtilizationReport({required this.utilization});

  final EnergyUtilization utilization;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Room utilization · ${utilization.termCode}',
        style: Theme.of(context).textTheme.titleMedium,
      ),
      EnergyDataStatusBadge(dataStatus: utilization.dataStatus),
      const SizedBox(height: 8),
      Text('Never used (${utilization.roomsNeverUsed.length})'),
      if (utilization.roomsNeverUsed.isEmpty)
        const Text('No rooms are listed as never used.')
      else
        Wrap(
          spacing: 8,
          children: [
            for (final room in utilization.roomsNeverUsed)
              Chip(label: Text(room)),
          ],
        ),
      const SizedBox(height: 12),
      Text(
        'Rooms under 50% seat utilization '
        '(${utilization.roomsUnder50PercentSeatUtilization.length})',
      ),
      if (utilization.roomsUnder50PercentSeatUtilization.isEmpty)
        const Text('No rooms are listed below 50%.')
      else
        for (final room in utilization.roomsUnder50PercentSeatUtilization)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(room.roomId),
            trailing: Text(
              room.seatUtilization == null
                  ? 'Unknown'
                  : '${(room.seatUtilization! * 100).toStringAsFixed(1)}%',
            ),
          ),
    ],
  );
}
