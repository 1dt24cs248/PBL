import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import 'campus_map_models.dart';

const bool useMockCampusMapRepository = false;

abstract interface class CampusMapRepository {
  Future<CampusFloorIndex> getFloorIndex();

  Future<CampusFloorPlan> getFloorPlan({
    required int floor,
    String? day,
    int? period,
    String? date,
  });

  Future<CampusRoute> getRoute({
    required String from,
    required String to,
    required String mode,
  });

  Future<List<CampusRoomRecord>> getRooms();
}

class ApiCampusMapRepository implements CampusMapRepository {
  const ApiCampusMapRepository(this._apiClient);

  final ApiClient _apiClient;

  @override
  Future<CampusFloorIndex> getFloorIndex() async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/floorplan',
    );
    return CampusFloorIndex.fromJson(response.data!);
  }

  @override
  Future<CampusFloorPlan> getFloorPlan({
    required int floor,
    String? day,
    int? period,
    String? date,
  }) async {
    if ((day == null) != (period == null) ||
        (date != null && (day != null || period == null))) {
      throw ArgumentError(
        'Use day and period together, or date and period together.',
      );
    }
    final queryParameters = <String, dynamic>{};
    if (day != null) {
      queryParameters['day'] = day;
      queryParameters['period'] = period;
    }
    if (date != null) {
      queryParameters['date'] = date;
      queryParameters['period'] = period;
    }
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/floorplan/$floor',
      queryParameters: queryParameters.isEmpty ? null : queryParameters,
    );
    return CampusFloorPlan.fromJson(response.data!);
  }

  @override
  Future<CampusRoute> getRoute({
    required String from,
    required String to,
    required String mode,
  }) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/nav/route',
      queryParameters: {'from': from, 'to': to, 'mode': mode},
    );
    return CampusRoute.fromJson(response.data!);
  }

  @override
  Future<List<CampusRoomRecord>> getRooms() async {
    final response = await _apiClient.dio.get<List<dynamic>>('/rooms');
    return response.data!
        .map((item) => CampusRoomRecord.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}

class MockCampusMapRepository implements CampusMapRepository {
  Never _notConfigured() => throw UnsupportedError(
    'Mock campus map mode is enabled, but no mock dataset is configured.',
  );

  @override
  Future<CampusFloorIndex> getFloorIndex() async => _notConfigured();

  @override
  Future<CampusFloorPlan> getFloorPlan({
    required int floor,
    String? day,
    int? period,
    String? date,
  }) async => _notConfigured();

  @override
  Future<CampusRoute> getRoute({
    required String from,
    required String to,
    required String mode,
  }) async => _notConfigured();

  @override
  Future<List<CampusRoomRecord>> getRooms() async => _notConfigured();
}

final campusMapRepositoryProvider = Provider<CampusMapRepository>((ref) {
  if (useMockCampusMapRepository) return MockCampusMapRepository();
  return ApiCampusMapRepository(ref.watch(apiClientProvider));
});

final campusFloorIndexProvider = FutureProvider<CampusFloorIndex>(
  (ref) => ref.watch(campusMapRepositoryProvider).getFloorIndex(),
  retry: (_, _) => null,
);

typedef CampusFloorQuery = ({int floor, String day, int period, String? date});

final campusFloorPlanProvider =
    FutureProvider.family<CampusFloorPlan, CampusFloorQuery>(
      (ref, query) => ref
          .watch(campusMapRepositoryProvider)
          .getFloorPlan(
            floor: query.floor,
            day: query.day,
            period: query.period,
            date: query.date,
          ),
      retry: (_, _) => null,
    );

final campusRoomsProvider = FutureProvider<List<CampusRoomRecord>>(
  (ref) => ref.watch(campusMapRepositoryProvider).getRooms(),
  retry: (_, _) => null,
);

class CampusMapSelection {
  const CampusMapSelection({
    required this.floor,
    required this.day,
    required this.period,
  });

  final int floor;
  final String day;
  final int period;
}

class CampusMapSelectionNotifier extends Notifier<CampusMapSelection> {
  @override
  CampusMapSelection build() =>
      const CampusMapSelection(floor: 0, day: 'Mon', period: 1);

  void selectFloor(int floor) {
    state = CampusMapSelection(
      floor: floor,
      day: state.day,
      period: state.period,
    );
  }

  void selectDay(String day) {
    state = CampusMapSelection(
      floor: state.floor,
      day: day,
      period: state.period,
    );
  }

  void selectPeriod(int period) {
    state = CampusMapSelection(
      floor: state.floor,
      day: state.day,
      period: period,
    );
  }
}

final campusMapSelectionProvider =
    NotifierProvider<CampusMapSelectionNotifier, CampusMapSelection>(
      CampusMapSelectionNotifier.new,
    );

class CampusRouteNotifier extends AsyncNotifier<CampusRoute?> {
  @override
  Future<CampusRoute?> build() async => null;

  Future<void> findRoute({
    required String from,
    required String to,
    required String mode,
  }) async {
    state = const AsyncLoading();
    try {
      final result = await ref
          .read(campusMapRepositoryProvider)
          .getRoute(from: from, to: to, mode: mode);
      state = AsyncData(result);
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
    }
  }
}

final campusRouteProvider =
    AsyncNotifierProvider<CampusRouteNotifier, CampusRoute?>(
      CampusRouteNotifier.new,
    );
