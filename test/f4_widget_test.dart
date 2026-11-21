import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:pbl/core/routing/app_router.dart';
import 'package:pbl/features/authentication/authentication_screen.dart';
import 'package:pbl/features/energy/energy_dashboard_screen.dart';
import 'package:pbl/features/energy/energy_models.dart';
import 'package:pbl/features/energy/energy_repository.dart';
import 'package:pbl/features/energy/energy_widgets.dart';
import 'package:pbl/features/energy/optimizer_screen.dart';
import 'package:pbl/features/energy/proposals_screen.dart';

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier(this.user);

  final AppUser? user;

  @override
  Future<AppUser?> build() async => user;
}

class _FakeEnergyRepository implements EnergyRepository {
  EnergyBaseline? baseline;
  EnergyUtilization? utilization;
  EnergyOptimizationResult? optimizationResult;
  EnergyProposalDetail? proposalDetail;
  Object? baselineError;
  Object? actionError;
  EnergyOptimizationRequest? lastOptimizationRequest;
  String? lastAction;
  int baselineCalls = 0;

  @override
  Future<EnergyBaseline> getBaseline() async {
    baselineCalls++;
    if (baselineError != null) throw baselineError!;
    return baseline ?? _baseline();
  }

  @override
  Future<EnergyUtilization> getUtilization() async =>
      utilization ?? _utilization();

  @override
  Future<EnergyOptimizationResult> optimize(
    EnergyOptimizationRequest request,
  ) async {
    lastOptimizationRequest = request;
    return optimizationResult ?? _optimizationResult();
  }

  @override
  Future<List<EnergyProposalSummary>> getProposals() async => [
    const EnergyProposalSummary(
      id: 'proposal-1',
      status: 'draft',
      termCode: '2026-27-ODD',
      dataStatus: 'SYNTHETIC',
      solverStatus: 'OPTIMAL',
    ),
  ];

  @override
  Future<EnergyProposalDetail> getProposal(String id) async =>
      proposalDetail ??
      EnergyProposalDetail(result: _optimizationResult(), status: 'submitted');

  @override
  Future<EnergyProposalStatus> updateProposal(String id, String action) async {
    lastAction = action;
    if (actionError != null) throw actionError!;
    return EnergyProposalStatus(
      id: id,
      status: action == 'approve' ? 'approved' : action,
      termCode: '2026-27-ODD',
      dataStatus: 'SYNTHETIC',
    );
  }
}

AppUser _user(String role) => AppUser(
  id: 1,
  username: 'test-user',
  fullName: 'Test User',
  role: role,
  category: role == 'student' ? 'Student' : 'Faculty',
  department: 'CSE',
);

EnergyBaseline _baseline() => EnergyBaseline(
  termCode: '2026-27-ODD',
  periodHours: 0.9166667,
  tariffInrPerKwh: 8.5,
  dataStatus: 'SYNTHETIC',
  timetableOccupancy: const EnergyOccupancyReport(
    rooms: [
      EnergyRoomUsage(
        roomId: 'A-F2-02',
        floor: 2,
        kwhWeek: 7.82,
        costWeekInr: 66.47,
        dataStatus: 'SYNTHETIC',
      ),
    ],
    floors: [EnergyFloorUsage(floor: 2, kwhWeek: 7.82, costWeekInr: 66.47)],
    block: EnergyBlockUsage(kwhWeek: 7.82, costWeekInr: 66.47),
    recordedRoomClashes: 2,
  ),
  flatBaseline: const EnergyFlatBaseline(
    label: 'Fixed equipment load × 6 h/day × 5 days/week',
    rooms: [
      EnergyRoomUsage(
        roomId: 'A-F2-02',
        kwhWeek: 21.3,
        costWeekInr: 181.05,
        dataStatus: null,
      ),
    ],
    floors: [EnergyFloorUsage(floor: 2, kwhWeek: 21.3)],
    block: EnergyBlockUsage(kwhWeek: 21.3),
  ),
);

EnergyUtilization _utilization() => const EnergyUtilization(
  termCode: '2026-27-ODD',
  periodsPerDay: 8,
  daysPerWeek: 6,
  dataStatus: 'INFERRED',
  rooms: [
    EnergyRoomUsage(
      roomId: 'A-F2-02',
      kwhWeek: null,
      costWeekInr: null,
      dataStatus: 'INFERRED',
      occupiedPeriodsWeek: 12,
      capacityEffective: 60,
      seatUtilization: 0.5,
    ),
  ],
  roomsNeverUsed: ['A-F2-12'],
  roomsUnder50PercentSeatUtilization: [
    EnergyLowSeatRoom(roomId: 'A-F2-03', seatUtilization: 0.25),
  ],
);

EnergyOptimizationResult _optimizationResult({
  String solverStatus = 'OPTIMAL',
  String? infeasibleReason,
}) => EnergyOptimizationResult(
  id: 'proposal-1',
  status: 'draft',
  termCode: '2026-27-ODD',
  solverStatus: solverStatus,
  solveTimeSeconds: 0.42,
  before: const OptimizationTotals(
    kwhWeek: 100,
    costWeekInr: 850,
    clashCount: 4,
  ),
  after: const OptimizationTotals(kwhWeek: 82, costWeekInr: 697, clashCount: 2),
  relocations: 3,
  affectedStudents: 120,
  changes: const [],
  dataStatus: 'SYNTHETIC',
  infeasibleReason: infeasibleReason,
);

Widget _harness(
  Widget child, {
  required _FakeEnergyRepository repository,
  String role = 'admin',
}) => ProviderScope(
  overrides: [
    authProvider.overrideWith(() => _FakeAuthNotifier(_user(role))),
    energyRepositoryProvider.overrideWithValue(repository),
  ],
  child: MaterialApp(home: child),
);

DioException _dioError(int status, Object data) {
  final request = RequestOptions(path: '/test');
  return DioException(
    requestOptions: request,
    response: Response(requestOptions: request, statusCode: status, data: data),
  );
}

void main() {
  testWidgets('energy dashboard shows reports and provenance labels', (
    tester,
  ) async {
    await tester.pumpWidget(
      _harness(
        const EnergyDashboardScreen(),
        repository: _FakeEnergyRepository(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Energy Dashboard'), findsOneWidget);
    expect(find.text('7.82'), findsOneWidget);
    expect(find.text('Top 10 consuming rooms'), findsOneWidget);
    expect(find.text('A-F2-12'), findsOneWidget);
    expect(find.text('A-F2-03'), findsOneWidget);
    expect(find.text('Synthetic wattage and tariff · SYNTHETIC'), findsWidgets);
    expect(find.text('Inferred'), findsOneWidget);
  });

  testWidgets('energy dashboard retries a 403 report failure', (tester) async {
    final repository = _FakeEnergyRepository()
      ..baselineError = _dioError(403, {'detail': 'Insufficient permissions'});
    await tester.pumpWidget(
      _harness(
        const EnergyDashboardScreen(),
        repository: repository,
        role: 'hod',
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('You do not have permission to view this information.'),
      findsOneWidget,
    );
    repository.baselineError = null;
    await tester.tap(find.text('Retry').first);
    await tester.pumpAndSettle();

    expect(repository.baselineCalls, 2);
    expect(find.text('Top 10 consuming rooms'), findsOneWidget);
  });

  testWidgets('optimizer submits documented options and renders infeasible', (
    tester,
  ) async {
    final repository = _FakeEnergyRepository()
      ..optimizationResult = _optimizationResult(
        solverStatus: 'INFEASIBLE',
        infeasibleReason: 'No eligible destination room.',
      );
    await tester.pumpWidget(
      _harness(const OptimizerScreen(), repository: repository),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('run_optimizer_button')));
    await tester.pumpAndSettle();

    expect(repository.lastOptimizationRequest?.movable, 'inferred_only');
    expect(repository.lastOptimizationRequest?.lockLabs, isTrue);
    expect(repository.lastOptimizationRequest?.lambdaMove, 1.0);
    expect(find.text('INFEASIBLE'), findsOneWidget);
    expect(find.text('No eligible destination room.'), findsOneWidget);
    expect(
      find.text(
        'Creates a proposal draft; official timetable records remain unchanged.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('proposal actions are role-gated and stale apply is explained', (
    tester,
  ) async {
    final repository = _FakeEnergyRepository()
      ..proposalDetail = EnergyProposalDetail(
        result: _optimizationResult(),
        status: 'submitted',
      )
      ..actionError = _dioError(409, {'detail': 'version conflict'});
    await tester.pumpWidget(
      _harness(
        const ProposalDetailScreen(proposalId: 'proposal-1'),
        repository: repository,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('proposal_approve_button')), findsOneWidget);
    expect(find.byKey(const Key('proposal_reject_button')), findsOneWidget);
    expect(find.byKey(const Key('proposal_submit_button')), findsNothing);
    expect(find.byKey(const Key('proposal_apply_button')), findsNothing);

    await tester.tap(find.byKey(const Key('proposal_approve_button')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();

    expect(repository.lastAction, 'approve');
    expect(
      find.text(
        'Data changed. Rerun the optimization and create a fresh proposal.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('energy error view maps 404, 422, network and 401 errors', (
    tester,
  ) async {
    final cases = <(Object, String, bool)>[
      (
        _dioError(403, {'detail': 'Insufficient permissions'}),
        'do not have permission',
        true,
      ),
      (_dioError(404, {'detail': 'Term not found'}), 'not found', true),
      (
        _dioError(422, {
          'detail': [
            {'msg': 'lambda_move must be non-negative'},
          ],
        }),
        'lambda_move must be non-negative',
        true,
      ),
      (
        DioException(
          requestOptions: RequestOptions(path: '/test'),
          type: DioExceptionType.connectionTimeout,
        ),
        'Network error',
        true,
      ),
      (
        _dioError(401, {'detail': 'Not authenticated'}),
        'session has expired',
        false,
      ),
    ];

    for (final (error, message, hasRetry) in cases) {
      var retried = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EnergyErrorView(error: error, onRetry: () => retried = true),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.textContaining(message), findsOneWidget);
      expect(find.text('Retry'), hasRetry ? findsOneWidget : findsNothing);
      if (hasRetry) {
        await tester.tap(find.text('Retry'));
        expect(retried, isTrue);
      }
    }
  });

  test('energy route guards match documented roles', () {
    expect(energyRouteRedirect('admin', '/energy'), isNull);
    expect(energyRouteRedirect('hod', '/energy'), isNull);
    expect(energyRouteRedirect('student', '/energy'), '/student');
    expect(energyRouteRedirect('teaching_faculty', '/energy'), '/faculty');
    expect(energyRouteRedirect('maintenance', '/energy'), '/management');
    expect(energyRouteRedirect('admin', '/energy/optimizer'), isNull);
    expect(energyRouteRedirect('hod', '/energy/optimizer'), '/energy');
    expect(energyRouteRedirect('student', '/energy/optimizer'), '/student');
  });
}
