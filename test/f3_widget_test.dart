import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:pbl/features/campus_map/campus_map_models.dart';
import 'package:pbl/features/campus_map/campus_map_painters.dart';
import 'package:pbl/features/campus_map/campus_map_repository.dart';
import 'package:pbl/features/campus_map/campus_map_screen.dart';
import 'package:pbl/features/timetable/campus_repository.dart';

class _FakeCampusMapRepository implements CampusMapRepository {
  int? lastFloor;
  String? lastDay;
  int? lastPeriod;
  String? lastFrom;
  String? lastTo;
  String? lastMode;
  Object? routeError;
  int routeCalls = 0;
  CampusRoute? route;

  @override
  Future<CampusFloorIndex> getFloorIndex() async => CampusFloorIndex(
    provenance: 'SYNTHETIC',
    canvas: const CampusCanvas(width: 1000, height: 600, metresPerPixel: 0.06),
    floors: [
      for (var floor = -1; floor <= 5; floor++)
        CampusFloorSummary(
          floor: floor,
          label: switch (floor) {
            -1 => 'Basement',
            0 => 'Ground Floor',
            _ => 'Floor $floor',
          },
          roomCount: 1,
        ),
    ],
  );

  @override
  Future<CampusFloorPlan> getFloorPlan({
    required int floor,
    String? day,
    int? period,
    String? date,
  }) async {
    lastFloor = floor;
    lastDay = day;
    lastPeriod = period;
    return _floorPlan(floor);
  }

  @override
  Future<CampusRoute> getRoute({
    required String from,
    required String to,
    required String mode,
  }) async {
    routeCalls++;
    lastFrom = from;
    lastTo = to;
    lastMode = mode;
    if (routeError != null) throw routeError!;
    return route ?? _route();
  }

  @override
  Future<List<CampusRoomRecord>> getRooms() async => const [
    CampusRoomRecord(
      number: 'A-F1-10',
      realLabel: 'Empty Room 10',
      aliases: ['110', 'A-108'],
      floor: 1,
      capacity: 30,
      capacityEffective: 30,
      dataStatus: 'SYNTHETIC',
      status: 'available',
    ),
    CampusRoomRecord(
      number: 'A-F3-05',
      realLabel: 'Computer Lab 05',
      aliases: ['305'],
      floor: 3,
      capacity: 30,
      capacityEffective: 30,
      dataStatus: 'SYNTHETIC',
      status: 'available',
    ),
  ];
}

CampusFloorPlan _floorPlan(int floor) => CampusFloorPlan(
  floor: floor,
  label: floor == -1 ? 'Basement' : 'Floor $floor',
  canvas: const CampusCanvas(width: 1000, height: 600),
  cores: const [
    CampusCore(
      geometry: CampusRect(x: 60, y: 270, width: 80, height: 60),
      label: 'West stairs',
    ),
  ],
  navNodes: const [],
  rooms: floor == 3
      ? const [
          CampusFloorRoom(
            roomId: 'A-F3-05',
            geometry: CampusRect(x: 780, y: 40, width: 160, height: 210),
            color: '#D8B4FE',
            status: 'available',
            capacityEffective: 30,
            dataStatus: 'SYNTHETIC',
            realLabel: 'Computer Lab 05',
            aliases: ['305'],
            occupancy: CampusRoomOccupancy(occupied: false, sessions: []),
          ),
        ]
      : const [],
);

CampusRoute _route() => const CampusRoute(
  fromRoom: 'A-F1-10',
  toRoom: 'A-F3-05',
  mode: 'lift',
  nodeKeys: [
    'f1_door_A-F1-10',
    'f1_corridor_n5',
    'f1_corridor_n4',
    'f1_corridor_n3',
    'f1_lifts_core_center',
    'f2_lifts_core_center',
    'f3_lifts_core_center',
    'f3_corridor_n3',
    'f3_corridor_n4',
    'f3_corridor_n5',
    'f3_door_A-F3-05',
  ],
  edges: [],
  distanceMetres: 70,
  routeCostSeconds: 98.3334,
  provenance: 'SYNTHETIC',
  path: [
    CampusRouteNode(
      nodeKey: 'f1_door_A-F1-10',
      floor: 1,
      x: 900,
      y: 350,
      kind: 'door',
      label: 'Door A-F1-10',
    ),
    CampusRouteNode(
      nodeKey: 'f1_lifts_core_center',
      floor: 1,
      x: 500,
      y: 300,
      kind: 'lifts_core_center',
      label: 'Center lift',
    ),
    CampusRouteNode(
      nodeKey: 'f2_lifts_core_center',
      floor: 2,
      x: 500,
      y: 300,
      kind: 'lifts_core_center',
      label: 'Center lift',
    ),
    CampusRouteNode(
      nodeKey: 'f3_lifts_core_center',
      floor: 3,
      x: 500,
      y: 300,
      kind: 'lifts_core_center',
      label: 'Center lift',
    ),
    CampusRouteNode(
      nodeKey: 'f3_corridor_n3',
      floor: 3,
      x: 500,
      y: 300,
      kind: 'corridor_n3',
      label: 'Corridor N3',
    ),
    CampusRouteNode(
      nodeKey: 'f3_corridor_n4',
      floor: 3,
      x: 700,
      y: 300,
      kind: 'corridor_n4',
      label: 'Corridor N4',
    ),
    CampusRouteNode(
      nodeKey: 'f3_corridor_n5',
      floor: 3,
      x: 900,
      y: 300,
      kind: 'corridor_n5',
      label: 'Corridor N5',
    ),
    CampusRouteNode(
      nodeKey: 'f3_door_A-F3-05',
      floor: 3,
      x: 900,
      y: 250,
      kind: 'door',
      label: 'Door A-F3-05',
    ),
  ],
  steps: [
    CampusRouteStep(
      instruction: 'Take the lift to Floor 2',
      floor: 2,
      fromNode: 'f1_lifts_core_center',
      toNode: 'f2_lifts_core_center',
      distanceMetres: 8,
      kind: 'lift',
    ),
    CampusRouteStep(
      instruction: 'Take the lift to Floor 3',
      floor: 3,
      fromNode: 'f2_lifts_core_center',
      toNode: 'f3_lifts_core_center',
      distanceMetres: 8,
      kind: 'lift',
    ),
  ],
  floorsVisited: [1, 2, 3],
);

Widget _mapHarness(Widget child, _FakeCampusMapRepository repository) =>
    ProviderScope(
      overrides: [campusMapRepositoryProvider.overrideWithValue(repository)],
      child: MaterialApp(home: child),
    );

Future<void> _selectRouteRooms(WidgetTester tester) async {
  await tester.enterText(find.byKey(const Key('from_room_field')), 'A-F1-10');
  await tester.pumpAndSettle();
  await tester.tap(find.text('A-F1-10').last);
  await tester.pumpAndSettle();

  await tester.enterText(find.byKey(const Key('to_room_field')), 'A-F3-05');
  await tester.pumpAndSettle();
  await tester.tap(find.text('A-F3-05').last);
  await tester.pumpAndSettle();
}

DioException _badRequest() {
  final request = RequestOptions(path: '/nav/route');
  return DioException(
    requestOptions: request,
    response: Response(
      requestOptions: request,
      statusCode: 422,
      data: {
        'detail': [
          {'msg': 'Unsupported mode'},
        ],
      },
    ),
  );
}

void main() {
  testWidgets('map tap hit-tests a room rectangle', (tester) async {
    CampusFloorRoom? selected;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CampusFloorMapView(
            plan: _floorPlan(3),
            onRoomTap: (room) => selected = room,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final mapRect = tester.getRect(
      find.byKey(const Key('campus_floor_canvas')),
    );
    await tester.tapAt(
      Offset(
        mapRect.left + mapRect.width * 0.86,
        mapRect.top + mapRect.height * 0.24,
      ),
    );
    await tester.pump();

    expect(selected?.roomId, 'A-F3-05');
    expect(
      hitTestCampusRoom(_floorPlan(3).rooms, const Offset(860, 145))?.roomId,
      'A-F3-05',
    );
  });

  testWidgets('route maps path nodes to each floor polyline', (tester) async {
    final route = _route();
    expect(routePolylineForFloor(route, 1), [
      const Offset(900, 350),
      const Offset(500, 300),
    ]);
    expect(routePolylineForFloor(route, 2), [const Offset(500, 300)]);
    expect(routePolylineForFloor(route, 3), [
      const Offset(500, 300),
      const Offset(500, 300),
      const Offset(700, 300),
      const Offset(900, 300),
      const Offset(900, 250),
    ]);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: CampusRouteFloorMap(route: route, floor: 2)),
      ),
    );
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is CustomPaint && widget.painter is CampusRouteFloorPainter,
      ),
      findsOneWidget,
    );
  });

  testWidgets('floor selector includes the documented -1 to 5 floors', (
    tester,
  ) async {
    final repository = _FakeCampusMapRepository();
    await tester.pumpWidget(_mapHarness(const CampusMapScreen(), repository));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('floor_selector')));
    await tester.pumpAndSettle();
    for (final floor in [
      'Basement (-1)',
      'Ground Floor (0)',
      'Floor 1 (1)',
      'Floor 2 (2)',
      'Floor 3 (3)',
      'Floor 4 (4)',
      'Floor 5 (5)',
    ]) {
      expect(find.text(floor), findsWidgets);
    }

    await tester.tap(find.text('Basement (-1)'));
    await tester.pumpAndSettle();
    expect(repository.lastFloor, -1);
    expect(repository.lastDay, 'Mon');
    expect(repository.lastPeriod, 1);
    expect(find.text('Basement'), findsOneWidget);
  });

  testWidgets('route screen explains 404 and 422 and retries network errors', (
    tester,
  ) async {
    final errors = <(Object, String, bool)>[
      (
        const TimetableFailure(404, 'Room not found'),
        'Unknown room. Select a room code, real label, or alias.',
        false,
      ),
      (_badRequest(), 'Invalid request: Unsupported mode', false),
      (
        const TimetableFailure(null, 'Connection failed'),
        'Network error. Check your connection.',
        true,
      ),
    ];

    for (final (error, message, canRetry) in errors) {
      final repository = _FakeCampusMapRepository()..routeError = error;
      await tester.pumpWidget(
        _mapHarness(const RouteNavigatorScreen(), repository),
      );
      await tester.pumpAndSettle();
      await _selectRouteRooms(tester);
      await tester.tap(find.byKey(const Key('find_route_button')));
      await tester.pumpAndSettle();

      expect(find.text(message), findsOneWidget);
      expect(find.text('Retry'), canRetry ? findsOneWidget : findsNothing);
      if (canRetry) {
        await tester.tap(find.text('Retry'));
        await tester.pumpAndSettle();
        expect(repository.routeCalls, 2);
      }
    }
  });

  testWidgets('room detail shows API capacity provenance and occupancy', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CampusRoomDetailSheet(
            room: _floorPlan(3).rooms.single,
            floor: 3,
            weekday: 'Mon',
            period: 1,
          ),
        ),
      ),
    );

    expect(find.text('Synthetic capacity'), findsOneWidget);
    expect(find.text('Occupied now: No'), findsOneWidget);
    expect(find.text('Sessions: 0'), findsOneWidget);
  });
}
