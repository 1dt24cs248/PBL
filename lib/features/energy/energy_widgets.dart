import 'package:dio/dio.dart';
import 'package:material_ui/material_ui.dart';

import 'energy_repository.dart';

class EnergyErrorView extends StatelessWidget {
  const EnergyErrorView({
    super.key,
    required this.error,
    required this.onRetry,
  });

  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final status = energyErrorStatus(error);
    final detail = energyErrorDetail(error);
    final message = switch (status) {
      401 => 'Your session has expired. Sign in again.',
      403 => 'You do not have permission to view this information.',
      404 => 'The requested term or proposal was not found.',
      409 => 'Data changed. Rerun the optimization before applying.',
      422 =>
        detail == null || detail.isEmpty
            ? 'The request was not valid.'
            : 'Invalid request: $detail',
      null when error is DioException =>
        'Network error. Check your connection and try again.',
      null => detail ?? 'Unable to load energy information.',
      _ => detail ?? 'The service could not complete the request.',
    };

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(message, textAlign: TextAlign.center),
            if (status != 401) ...[
              const SizedBox(height: 12),
              OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
            ],
          ],
        ),
      ),
    );
  }
}

class EnergyDataStatusBadge extends StatelessWidget {
  const EnergyDataStatusBadge({super.key, required this.dataStatus});

  final String dataStatus;

  @override
  Widget build(BuildContext context) {
    final label = switch (dataStatus) {
      'SYNTHETIC' => 'Synthetic',
      'INFERRED' => 'Inferred',
      'REAL_DSATM_PDF' => 'Real DSATM PDF',
      _ => dataStatus,
    };
    return Chip(
      label: Text(label),
      visualDensity: VisualDensity.compact,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }
}

class SyntheticEnergyLabel extends StatelessWidget {
  const SyntheticEnergyLabel({super.key, required this.dataStatus});

  final String dataStatus;

  @override
  Widget build(BuildContext context) => Text(
    'Synthetic wattage and tariff · $dataStatus',
    style: Theme.of(context).textTheme.labelSmall,
  );
}
