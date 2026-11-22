class EnergyRoomUsage {
  const EnergyRoomUsage({
    required this.roomId,
    required this.kwhWeek,
    required this.costWeekInr,
    required this.dataStatus,
    this.floor,
    this.connectedKw,
    this.occupiedPeriodsWeek,
    this.capacityEffective,
    this.seatUtilization,
  });

  factory EnergyRoomUsage.fromJson(Map<String, dynamic> json) =>
      EnergyRoomUsage(
        roomId: json['room_id'] as String,
        kwhWeek: (json['kwh_week'] as num?)?.toDouble(),
        costWeekInr: (json['cost_week_inr'] as num?)?.toDouble(),
        dataStatus: json['data_status'] as String?,
        floor: json['floor'] as int?,
        connectedKw: (json['connected_kw'] as num?)?.toDouble(),
        occupiedPeriodsWeek: json['occupied_periods_week'] as int?,
        capacityEffective: json['capacity_effective'] as int?,
        seatUtilization: (json['seat_utilization'] as num?)?.toDouble(),
      );

  final String roomId;
  final double? kwhWeek;
  final double? costWeekInr;
  final String? dataStatus;
  final int? floor;
  final double? connectedKw;
  final int? occupiedPeriodsWeek;
  final int? capacityEffective;
  final double? seatUtilization;
}

class EnergyFloorUsage {
  const EnergyFloorUsage({
    required this.floor,
    this.kwhWeek,
    this.costWeekInr,
    this.occupiedPeriodsWeek,
  });

  factory EnergyFloorUsage.fromJson(Map<String, dynamic> json) =>
      EnergyFloorUsage(
        floor: json['floor'] as int,
        kwhWeek: (json['kwh_week'] as num?)?.toDouble(),
        costWeekInr: (json['cost_week_inr'] as num?)?.toDouble(),
        occupiedPeriodsWeek: json['occupied_periods_week'] as int?,
      );

  final int floor;
  final double? kwhWeek;
  final double? costWeekInr;
  final int? occupiedPeriodsWeek;
}

class EnergyBlockUsage {
  const EnergyBlockUsage({
    required this.kwhWeek,
    this.costWeekInr,
    this.occupiedPeriodsWeek,
    this.clashCount,
  });

  factory EnergyBlockUsage.fromJson(Map<String, dynamic> json) =>
      EnergyBlockUsage(
        kwhWeek: (json['kwh_week'] as num).toDouble(),
        costWeekInr: (json['cost_week_inr'] as num?)?.toDouble(),
        occupiedPeriodsWeek: json['occupied_periods_week'] as int?,
        clashCount: json['clash_count'] as int?,
      );

  final double kwhWeek;
  final double? costWeekInr;
  final int? occupiedPeriodsWeek;
  final int? clashCount;
}

class EnergyOccupancyReport {
  const EnergyOccupancyReport({
    required this.rooms,
    required this.floors,
    required this.block,
    required this.recordedRoomClashes,
  });

  factory EnergyOccupancyReport.fromJson(
    Map<String, dynamic> json,
  ) => EnergyOccupancyReport(
    rooms: (json['rooms'] as List<dynamic>)
        .map((item) => EnergyRoomUsage.fromJson(item as Map<String, dynamic>))
        .toList(),
    floors: (json['floors'] as List<dynamic>)
        .map((item) => EnergyFloorUsage.fromJson(item as Map<String, dynamic>))
        .toList(),
    block: EnergyBlockUsage.fromJson(json['block'] as Map<String, dynamic>),
    recordedRoomClashes: json['recorded_room_clashes'] as int,
  );

  final List<EnergyRoomUsage> rooms;
  final List<EnergyFloorUsage> floors;
  final EnergyBlockUsage block;
  final int recordedRoomClashes;
}

class EnergyFlatBaseline {
  const EnergyFlatBaseline({
    required this.label,
    required this.rooms,
    required this.floors,
    required this.block,
  });

  factory EnergyFlatBaseline.fromJson(
    Map<String, dynamic> json,
  ) => EnergyFlatBaseline(
    label: json['label'] as String,
    rooms: (json['rooms'] as List<dynamic>)
        .map((item) => EnergyRoomUsage.fromJson(item as Map<String, dynamic>))
        .toList(),
    floors: (json['floors'] as List<dynamic>)
        .map((item) => EnergyFloorUsage.fromJson(item as Map<String, dynamic>))
        .toList(),
    block: EnergyBlockUsage.fromJson(json['block'] as Map<String, dynamic>),
  );

  final String label;
  final List<EnergyRoomUsage> rooms;
  final List<EnergyFloorUsage> floors;
  final EnergyBlockUsage block;
}

class EnergyBaseline {
  const EnergyBaseline({
    required this.termCode,
    required this.periodHours,
    required this.tariffInrPerKwh,
    required this.dataStatus,
    required this.timetableOccupancy,
    required this.flatBaseline,
  });

  factory EnergyBaseline.fromJson(Map<String, dynamic> json) => EnergyBaseline(
    termCode: json['term_code'] as String,
    periodHours: (json['period_hours'] as num).toDouble(),
    tariffInrPerKwh: (json['tariff_inr_per_kwh'] as num).toDouble(),
    dataStatus: json['data_status'] as String,
    timetableOccupancy: EnergyOccupancyReport.fromJson(
      json['timetable_occupancy'] as Map<String, dynamic>,
    ),
    flatBaseline: EnergyFlatBaseline.fromJson(
      json['flat_spec_baseline_6h_x_5days'] as Map<String, dynamic>,
    ),
  );

  final String termCode;
  final double periodHours;
  final double tariffInrPerKwh;
  final String dataStatus;
  final EnergyOccupancyReport timetableOccupancy;
  final EnergyFlatBaseline flatBaseline;
}

class EnergyLowSeatRoom {
  const EnergyLowSeatRoom({
    required this.roomId,
    required this.seatUtilization,
  });

  factory EnergyLowSeatRoom.fromJson(Map<String, dynamic> json) =>
      EnergyLowSeatRoom(
        roomId: json['room_id'] as String,
        seatUtilization: (json['seat_utilization'] as num?)?.toDouble(),
      );

  final String roomId;
  final double? seatUtilization;
}

class EnergyUtilization {
  const EnergyUtilization({
    required this.termCode,
    required this.periodsPerDay,
    required this.daysPerWeek,
    required this.dataStatus,
    required this.rooms,
    required this.roomsNeverUsed,
    required this.roomsUnder50PercentSeatUtilization,
  });

  factory EnergyUtilization.fromJson(
    Map<String, dynamic> json,
  ) => EnergyUtilization(
    termCode: json['term_code'] as String,
    periodsPerDay: json['periods_per_day'] as int,
    daysPerWeek: json['days_per_week'] as int,
    dataStatus: json['data_status'] as String,
    rooms: (json['rooms'] as List<dynamic>)
        .map((item) => EnergyRoomUsage.fromJson(item as Map<String, dynamic>))
        .toList(),
    roomsNeverUsed: (json['rooms_never_used'] as List<dynamic>).cast<String>(),
    roomsUnder50PercentSeatUtilization:
        (json['rooms_under_50_percent_seat_utilization'] as List<dynamic>)
            .map(
              (item) =>
                  EnergyLowSeatRoom.fromJson(item as Map<String, dynamic>),
            )
            .toList(),
  );

  final String termCode;
  final int periodsPerDay;
  final int daysPerWeek;
  final String dataStatus;
  final List<EnergyRoomUsage> rooms;
  final List<String> roomsNeverUsed;
  final List<EnergyLowSeatRoom> roomsUnder50PercentSeatUtilization;
}

class EnergyOptimizationRequest {
  const EnergyOptimizationRequest({
    required this.movable,
    required this.lockLabs,
    required this.forbidFloors,
    required this.lambdaMove,
    this.sections = const [],
    this.term = '2026-27-ODD',
  });

  final String term;
  final String movable;
  final List<String> sections;
  final bool lockLabs;
  final List<int> forbidFloors;
  final double lambdaMove;

  Map<String, dynamic> toJson() => {
    'term': term,
    'movable': movable,
    'sections': sections,
    'lock_labs': lockLabs,
    'forbid_floors': forbidFloors,
    'lambda_move': lambdaMove,
  };
}

class OptimizationTotals {
  const OptimizationTotals({
    required this.kwhWeek,
    required this.costWeekInr,
    required this.clashCount,
  });

  factory OptimizationTotals.fromJson(Map<String, dynamic> json) =>
      OptimizationTotals(
        kwhWeek: (json['kwh_week'] as num).toDouble(),
        costWeekInr: (json['cost_week_inr'] as num).toDouble(),
        clashCount: json['clash_count'] as int,
      );

  final double kwhWeek;
  final double costWeekInr;
  final int clashCount;
}

class EnergyChange {
  const EnergyChange({
    required this.sessionId,
    required this.fromRoom,
    required this.toRoom,
    required this.expectedSessionVersion,
    required this.expectedFromRoomVersion,
    required this.expectedToRoomVersion,
  });

  factory EnergyChange.fromJson(Map<String, dynamic> json) => EnergyChange(
    sessionId: json['session_id'] as int,
    fromRoom: json['from_room'] as String,
    toRoom: json['to_room'] as String,
    expectedSessionVersion: json['expected_session_version'] as int,
    expectedFromRoomVersion: json['expected_from_room_version'] as int,
    expectedToRoomVersion: json['expected_to_room_version'] as int,
  );

  final int sessionId;
  final String fromRoom;
  final String toRoom;
  final int expectedSessionVersion;
  final int expectedFromRoomVersion;
  final int expectedToRoomVersion;
}

class EnergyOptimizationResult {
  const EnergyOptimizationResult({
    required this.id,
    required this.status,
    required this.termCode,
    required this.solverStatus,
    required this.solveTimeSeconds,
    required this.before,
    required this.after,
    required this.relocations,
    required this.affectedStudents,
    required this.changes,
    required this.dataStatus,
    this.infeasibleReason,
  });

  factory EnergyOptimizationResult.fromJson(
    Map<String, dynamic> json,
  ) => EnergyOptimizationResult(
    id: json['id'] as String,
    status: json['status'] as String,
    termCode: json['term_code'] as String,
    solverStatus: json['solver_status'] as String,
    solveTimeSeconds: (json['solve_time_s'] as num).toDouble(),
    before: OptimizationTotals.fromJson(json['before'] as Map<String, dynamic>),
    after: OptimizationTotals.fromJson(json['after'] as Map<String, dynamic>),
    relocations: json['relocations'] as int,
    affectedStudents: json['affected_students'] as int,
    changes: (json['changes'] as List<dynamic>)
        .map((item) => EnergyChange.fromJson(item as Map<String, dynamic>))
        .toList(),
    dataStatus: json['data_status'] as String,
    infeasibleReason: json['infeasible_reason'] as String?,
  );

  final String id;
  final String status;
  final String termCode;
  final String solverStatus;
  final double solveTimeSeconds;
  final OptimizationTotals before;
  final OptimizationTotals after;
  final int relocations;
  final int affectedStudents;
  final List<EnergyChange> changes;
  final String dataStatus;
  final String? infeasibleReason;
}

class EnergyProposalSummary {
  const EnergyProposalSummary({
    required this.id,
    required this.status,
    required this.termCode,
    required this.dataStatus,
    this.solverStatus,
  });

  factory EnergyProposalSummary.fromJson(Map<String, dynamic> json) =>
      EnergyProposalSummary(
        id: json['id'] as String,
        status: json['status'] as String,
        termCode: json['term_code'] as String,
        dataStatus: json['data_status'] as String,
        solverStatus: json['solver_status'] as String?,
      );

  final String id;
  final String status;
  final String termCode;
  final String dataStatus;
  final String? solverStatus;
}

class EnergyProposalDetail {
  const EnergyProposalDetail({required this.result, required this.status});

  factory EnergyProposalDetail.fromJson(Map<String, dynamic> json) =>
      EnergyProposalDetail(
        result: EnergyOptimizationResult.fromJson(json),
        status: json['status'] as String,
      );

  final EnergyOptimizationResult result;
  final String status;
}

class EnergyProposalStatus {
  const EnergyProposalStatus({
    required this.id,
    required this.status,
    required this.termCode,
    required this.dataStatus,
  });

  factory EnergyProposalStatus.fromJson(Map<String, dynamic> json) =>
      EnergyProposalStatus(
        id: json['id'] as String,
        status: json['status'] as String,
        termCode: json['term_code'] as String,
        dataStatus: json['data_status'] as String,
      );

  final String id;
  final String status;
  final String termCode;
  final String dataStatus;
}
