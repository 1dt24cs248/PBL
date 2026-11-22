import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import 'energy_models.dart';

const bool useMockEnergyRepository = false;

abstract interface class EnergyRepository {
  Future<EnergyBaseline> getBaseline();
  Future<EnergyUtilization> getUtilization();
  Future<EnergyOptimizationResult> optimize(EnergyOptimizationRequest request);
  Future<List<EnergyProposalSummary>> getProposals();
  Future<EnergyProposalDetail> getProposal(String id);
  Future<EnergyProposalStatus> updateProposal(String id, String action);
}

class ApiEnergyRepository implements EnergyRepository {
  const ApiEnergyRepository(this._apiClient);

  final ApiClient _apiClient;
  Dio get _dio => _apiClient.dio;

  @override
  Future<EnergyBaseline> getBaseline() async {
    final response = await _dio.get<Map<String, dynamic>>('/energy/baseline');
    return EnergyBaseline.fromJson(response.data!);
  }

  @override
  Future<EnergyUtilization> getUtilization() async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/energy/utilization',
    );
    return EnergyUtilization.fromJson(response.data!);
  }

  @override
  Future<EnergyOptimizationResult> optimize(
    EnergyOptimizationRequest request,
  ) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/optimizer/energy',
      data: request.toJson(),
    );
    return EnergyOptimizationResult.fromJson(response.data!);
  }

  @override
  Future<List<EnergyProposalSummary>> getProposals() async {
    final response = await _dio.get<List<dynamic>>('/proposals');
    return response.data!
        .map(
          (item) =>
              EnergyProposalSummary.fromJson(item as Map<String, dynamic>),
        )
        .toList();
  }

  @override
  Future<EnergyProposalDetail> getProposal(String id) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/proposals/${Uri.encodeComponent(id)}',
    );
    return EnergyProposalDetail.fromJson(response.data!);
  }

  @override
  Future<EnergyProposalStatus> updateProposal(String id, String action) async {
    const actions = {'submit', 'approve', 'reject', 'apply'};
    if (!actions.contains(action)) {
      throw ArgumentError.value(
        action,
        'action',
        'Unsupported proposal action',
      );
    }
    final response = await _dio.post<Map<String, dynamic>>(
      '/proposals/${Uri.encodeComponent(id)}/$action',
      data: const <String, dynamic>{},
    );
    return EnergyProposalStatus.fromJson(response.data!);
  }
}

class MockEnergyRepository implements EnergyRepository {
  Never _notConfigured() => throw UnsupportedError(
    'Mock energy mode is enabled, but no mock dataset is configured.',
  );

  @override
  Future<EnergyBaseline> getBaseline() async => _notConfigured();

  @override
  Future<EnergyUtilization> getUtilization() async => _notConfigured();

  @override
  Future<EnergyOptimizationResult> optimize(
    EnergyOptimizationRequest request,
  ) async => _notConfigured();

  @override
  Future<List<EnergyProposalSummary>> getProposals() async => _notConfigured();

  @override
  Future<EnergyProposalDetail> getProposal(String id) async => _notConfigured();

  @override
  Future<EnergyProposalStatus> updateProposal(String id, String action) async =>
      _notConfigured();
}

final energyRepositoryProvider = Provider<EnergyRepository>((ref) {
  if (useMockEnergyRepository) return MockEnergyRepository();
  return ApiEnergyRepository(ref.watch(apiClientProvider));
});

final energyBaselineProvider = FutureProvider<EnergyBaseline>(
  (ref) => ref.watch(energyRepositoryProvider).getBaseline(),
  retry: (_, _) => null,
);

final energyUtilizationProvider = FutureProvider<EnergyUtilization>(
  (ref) => ref.watch(energyRepositoryProvider).getUtilization(),
  retry: (_, _) => null,
);

final energyProposalsProvider = FutureProvider<List<EnergyProposalSummary>>(
  (ref) => ref.watch(energyRepositoryProvider).getProposals(),
  retry: (_, _) => null,
);

final energyProposalProvider =
    FutureProvider.family<EnergyProposalDetail, String>(
      (ref, id) => ref.watch(energyRepositoryProvider).getProposal(id),
      retry: (_, _) => null,
    );

class EnergyOptimizerNotifier extends AsyncNotifier<EnergyOptimizationResult?> {
  @override
  Future<EnergyOptimizationResult?> build() async => null;

  Future<EnergyOptimizationResult> run(
    EnergyOptimizationRequest request,
  ) async {
    state = const AsyncLoading();
    try {
      final result = await ref.read(energyRepositoryProvider).optimize(request);
      state = AsyncData(result);
      return result;
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      rethrow;
    }
  }
}

final energyOptimizerProvider =
    AsyncNotifierProvider<EnergyOptimizerNotifier, EnergyOptimizationResult?>(
      EnergyOptimizerNotifier.new,
    );

class EnergyProposalActionNotifier
    extends AsyncNotifier<EnergyProposalStatus?> {
  @override
  Future<EnergyProposalStatus?> build() async => null;

  Future<EnergyProposalStatus> performAction(String id, String action) async {
    state = const AsyncLoading();
    try {
      final result = await ref
          .read(energyRepositoryProvider)
          .updateProposal(id, action);
      state = AsyncData(result);
      return result;
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      rethrow;
    }
  }
}

final energyProposalActionProvider =
    AsyncNotifierProvider<EnergyProposalActionNotifier, EnergyProposalStatus?>(
      EnergyProposalActionNotifier.new,
    );

String? energyErrorDetail(Object error) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is List<dynamic>) {
        return detail
            .map((item) {
              if (item is Map<String, dynamic>) return item['msg']?.toString();
              return item.toString();
            })
            .whereType<String>()
            .join('; ');
      }
      if (detail != null) return detail.toString();
    }
    if (data is String && data.isNotEmpty) return data;
    return error.message;
  }
  return error.toString();
}

int? energyErrorStatus(Object error) =>
    error is DioException ? error.response?.statusCode : null;
