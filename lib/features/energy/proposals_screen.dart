import 'package:dio/dio.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/authentication/authentication_screen.dart';
import 'energy_models.dart';
import 'energy_repository.dart';
import 'energy_widgets.dart';

class ProposalListScreen extends ConsumerWidget {
  const ProposalListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final proposals = ref.watch(energyProposalsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Energy Proposals')),
      body: proposals.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => EnergyErrorView(
          error: error,
          onRetry: () => ref.invalidate(energyProposalsProvider),
        ),
        data: (items) {
          if (items.isEmpty) {
            return const Center(child: Text('No proposals are available.'));
          }
          return ListView.builder(
            itemCount: items.length,
            itemBuilder: (context, index) {
              final proposal = items[index];
              return Card(
                child: ListTile(
                  key: Key('proposal_${proposal.id}'),
                  title: Text(proposal.id),
                  subtitle: Text(
                    '${proposal.termCode} · ${proposal.solverStatus ?? 'Status unavailable'}',
                  ),
                  trailing: EnergyDataStatusBadge(
                    dataStatus: proposal.dataStatus,
                  ),
                  leading: Text(proposal.status),
                  onTap: () => context.go('/proposals/${proposal.id}'),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class ProposalDetailScreen extends ConsumerWidget {
  const ProposalDetailScreen({super.key, required this.proposalId});

  final String proposalId;

  Future<void> _confirmAction(
    BuildContext context,
    WidgetRef ref,
    String action,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('${_actionLabel(action)} proposal?'),
        content: Text(
          action == 'apply'
              ? 'Applying checks the saved versions and updates official room assignments only if they still match.'
              : 'Confirm that you want to $action this proposal.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;

    await _performAction(context, ref, action);
  }

  Future<void> _performAction(
    BuildContext context,
    WidgetRef ref,
    String action,
  ) async {
    try {
      final result = await ref
          .read(energyProposalActionProvider.notifier)
          .performAction(proposalId, action);
      ref.invalidate(energyProposalProvider(proposalId));
      ref.invalidate(energyProposalsProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Proposal ${result.status}.')));
      }
    } catch (error) {
      if (context.mounted) {
        final status = energyErrorStatus(error);
        final message = status == 409
            ? 'Data changed. Rerun the optimization and create a fresh proposal.'
            : energyErrorDetail(error) ?? 'Unable to update the proposal.';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            action: error is DioException && error.response == null
                ? SnackBarAction(
                    label: 'Retry',
                    onPressed: () {
                      _performAction(context, ref, action);
                    },
                  )
                : null,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final proposal = ref.watch(energyProposalProvider(proposalId));
    final role = ref.watch(authProvider).value?.role;
    return Scaffold(
      appBar: AppBar(title: const Text('Proposal details')),
      body: proposal.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => EnergyErrorView(
          error: error,
          onRetry: () => ref.invalidate(energyProposalProvider(proposalId)),
        ),
        data: (detail) => _ProposalDetailContent(
          detail: detail,
          role: role,
          onAction: (action) => _confirmAction(context, ref, action),
        ),
      ),
    );
  }
}

class _ProposalDetailContent extends StatelessWidget {
  const _ProposalDetailContent({
    required this.detail,
    required this.role,
    required this.onAction,
  });

  final EnergyProposalDetail detail;
  final String? role;
  final ValueChanged<String> onAction;

  @override
  Widget build(BuildContext context) {
    final result = detail.result;
    final isAdmin = role == 'admin';
    final canApprove = isAdmin || role == 'hod';
    final actions = <Widget>[];
    if (isAdmin && detail.status == 'draft') {
      actions.add(_actionButton('submit'));
    }
    if (canApprove && detail.status == 'submitted') {
      actions.add(_actionButton('approve'));
    }
    if (isAdmin && (detail.status == 'draft' || detail.status == 'submitted')) {
      actions.add(_actionButton('reject'));
    }
    if (isAdmin && detail.status == 'approved') {
      actions.add(_actionButton('apply'));
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(result.id, style: Theme.of(context).textTheme.titleLarge),
        Text('Workflow status: ${detail.status}'),
        Text('Solver status: ${result.solverStatus}'),
        Text('Term: ${result.termCode}'),
        Text('Solve time: ${result.solveTimeSeconds.toStringAsFixed(2)} s'),
        EnergyDataStatusBadge(dataStatus: result.dataStatus),
        SyntheticEnergyLabel(dataStatus: result.dataStatus),
        if (result.solverStatus == 'INFEASIBLE')
          Text(
            result.infeasibleReason ??
                'The API did not provide an infeasibility reason.',
          ),
        const SizedBox(height: 12),
        _ProposalTotals(
          label: 'Before',
          totals: result.before,
          dataStatus: result.dataStatus,
        ),
        _ProposalTotals(
          label: 'After',
          totals: result.after,
          dataStatus: result.dataStatus,
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
        if (actions.isNotEmpty) ...[
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: actions),
        ],
      ],
    );
  }

  Widget _actionButton(String action) => OutlinedButton(
    key: Key('proposal_${action}_button'),
    onPressed: () => onAction(action),
    child: Text(_actionLabel(action)),
  );
}

class _ProposalTotals extends StatelessWidget {
  const _ProposalTotals({
    required this.label,
    required this.totals,
    required this.dataStatus,
  });

  final String label;
  final OptimizationTotals totals;
  final String dataStatus;

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
        SyntheticEnergyLabel(dataStatus: dataStatus),
      ],
    ),
  );
}

String _actionLabel(String action) =>
    '${action[0].toUpperCase()}${action.substring(1)}';
