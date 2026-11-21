import 'package:material_ui/material_ui.dart';

import '../../features/timetable/campus_repository.dart';

class ApiErrorView extends StatelessWidget {
  const ApiErrorView({
    super.key,
    required this.error,
    required this.onRetry,
    this.notFoundMessage,
  });

  final Object error;
  final VoidCallback onRetry;
  final String? notFoundMessage;

  @override
  Widget build(BuildContext context) {
    final failure = TimetableFailure.from(error);
    final message = switch (failure.statusCode) {
      401 => 'Your session expired. Redirecting to login.',
      403 => 'You do not have permission to view this data.',
      404 => notFoundMessage ?? 'No matching data was found.',
      422 => 'Invalid request: ${failure.message}',
      _ when failure.isNetworkError => 'Network error. Check your connection.',
      _ => 'Unable to load data.',
    };
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined, size: 40),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            if (failure.isNetworkError) ...[
              const SizedBox(height: 12),
              OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
            ],
          ],
        ),
      ),
    );
  }
}
