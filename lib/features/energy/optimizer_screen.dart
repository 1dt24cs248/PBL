import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'energy_models.dart';
import 'energy_repository.dart';
import 'energy_widgets.dart';

class OptimizerScreen extends ConsumerStatefulWidget {
  const OptimizerScreen({super.key});

  @override
  ConsumerState<OptimizerScreen> createState() => _OptimizerScreenState();
}

class _OptimizerScreenState extends ConsumerState<OptimizerScreen> {
  final _formKey = GlobalKey<FormState>();
  final _sectionsController = TextEditingController();
  final _lambdaController = TextEditingController(text: '1.0');
  String _movable = 'inferred_only';
  bool _lockLabs = true;
  final Set<int> _forbidFloors = {};

  @override
  void dispose() {
    _sectionsController.dispose();
    _lambdaController.dispose();
    super.dispose();
  }

  Future<void> _run() async {
    if (!_formKey.currentState!.validate()) return;
    final request = EnergyOptimizationRequest(
      movable: _movable,
      sections: _movable == 'selected_sections'
          ? _sectionsController.text
                .split(',')
                .map((section) => section.trim())
                .where((section) => section.isNotEmpty)
                .toList()
          : const [],
      lockLabs: _lockLabs,
      forbidFloors: _forbidFloors.toList()..sort(),
      lambdaMove: double.parse(_lambdaController.text.trim()),
    );
    try {
      await ref.read(energyOptimizerProvider.notifier).run(request);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(energyErrorDetail(error) ?? 'Optimization failed.'),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = ref.watch(energyOptimizerProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Energy Optimizer')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Creates a proposal draft; official timetable records remain unchanged.',
          ),
          const SizedBox(height: 12),
          Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: _movable,
                  decoration: const InputDecoration(labelText: 'Movable mode'),
                  items: const [
                    DropdownMenuItem(
                      value: 'inferred_only',
                      child: Text('Inferred only'),
                    ),
                    DropdownMenuItem(value: 'all', child: Text('All')),
                    DropdownMenuItem(
                      value: 'selected_sections',
                      child: Text('Selected sections'),
                    ),
                  ],
                  onChanged: result.isLoading
                      ? null
                      : (value) {
                          if (value != null) setState(() => _movable = value);
                        },
                ),
                if (_movable == 'selected_sections')
                  TextFormField(
                    key: const Key('selected_sections_field'),
                    controller: _sectionsController,
                    decoration: const InputDecoration(
                      labelText: 'Section codes',
                      hintText: 'Comma-separated API section codes',
                    ),
                    validator: (value) {
                      if (_movable == 'selected_sections' &&
                          (value == null || value.trim().isEmpty)) {
                        return 'Enter at least one section code';
                      }
                      return null;
                    },
                  ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Lock labs'),
                  value: _lockLabs,
                  onChanged: result.isLoading
                      ? null
                      : (value) => setState(() => _lockLabs = value),
                ),
                Text(
                  'Forbid floors',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                Wrap(
                  spacing: 8,
                  children: [
                    for (var floor = -1; floor <= 5; floor++)
                      FilterChip(
                        label: Text('$floor'),
                        selected: _forbidFloors.contains(floor),
                        onSelected: result.isLoading
                            ? null
                            : (selected) => setState(() {
                                if (selected) {
                                  _forbidFloors.add(floor);
                                } else {
                                  _forbidFloors.remove(floor);
                                }
                              }),
                      ),
                  ],
                ),
                TextFormField(
                  key: const Key('lambda_move_field'),
                  controller: _lambdaController,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  decoration: const InputDecoration(labelText: 'lambda_move'),
                  validator: (value) {
                    final lambda = double.tryParse(value?.trim() ?? '');
                    if (lambda == null || !lambda.isFinite || lambda < 0) {
                      return 'Enter a non-negative number';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                FilledButton.icon(
                  key: const Key('run_optimizer_button'),
                  onPressed: result.isLoading ? null : _run,
                  icon: const Icon(Icons.play_arrow),
                  label: result.isLoading
                      ? const Text('Running…')
                      : const Text('Run optimizer'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          if (result.isLoading)
            const Center(child: CircularProgressIndicator())
          else if (result.hasError)
            EnergyErrorView(error: result.error!, onRetry: _run)
          else if (result.value != null)
            _OptimizationResultCard(result: result.value!),
        ],
      ),
    );
  }
}

class _OptimizationResultCard extends StatelessWidget {
  const _OptimizationResultCard({required this.result});

  final EnergyOptimizationResult result;

  @override
  Widget build(BuildContext context) {
    final infeasible = result.solverStatus == 'INFEASIBLE';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              infeasible
                  ? 'INFEASIBLE'
                  : 'Solver status: ${result.solverStatus}',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: infeasible ? Theme.of(context).colorScheme.error : null,
              ),
            ),
            Text('Proposal ${result.id} · ${result.status}'),
            Text('Solve time: ${result.solveTimeSeconds.toStringAsFixed(2)} s'),
            EnergyDataStatusBadge(dataStatus: result.dataStatus),
            SyntheticEnergyLabel(dataStatus: result.dataStatus),
            if (infeasible)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  result.infeasibleReason ??
                      'The API did not provide an infeasibility reason.',
                ),
              ),
            const SizedBox(height: 12),
            _EnergyResultTotals(
              label: 'Before',
              totals: result.before,
              status: result.dataStatus,
            ),
            _EnergyResultTotals(
              label: 'After',
              totals: result.after,
              status: result.dataStatus,
            ),
            Text('Relocations: ${result.relocations}'),
            Text('Students affected: ${result.affectedStudents}'),
            const SizedBox(height: 8),
            Text('Changes', style: Theme.of(context).textTheme.titleMedium),
            if (result.changes.isEmpty)
              const Text('No changes were returned.')
            else
              for (final change in result.changes)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('${change.fromRoom} → ${change.toRoom}'),
                  subtitle: Text('Session ${change.sessionId}'),
                ),
          ],
        ),
      ),
    );
  }
}

class _EnergyResultTotals extends StatelessWidget {
  const _EnergyResultTotals({
    required this.label,
    required this.totals,
    required this.status,
  });

  final String label;
  final OptimizationTotals totals;
  final String status;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.titleSmall),
        Text(
          '${totals.kwhWeek.toStringAsFixed(2)} kWh / week · '
          'Rs ${totals.costWeekInr.toStringAsFixed(2)} / week',
        ),
        SyntheticEnergyLabel(dataStatus: status),
      ],
    ),
  );
}
