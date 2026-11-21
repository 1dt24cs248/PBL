class CampusCanvas {
  const CampusCanvas({
    required this.width,
    required this.height,
    this.metresPerPixel,
  });

  factory CampusCanvas.fromJson(Map<String, dynamic> json) => CampusCanvas(
    width: (json['width'] as num).toDouble(),
    height: (json['height'] as num).toDouble(),
    metresPerPixel: (json['metres_per_pixel'] as num?)?.toDouble(),
  );

  final double width;
  final double height;
  final double? metresPerPixel;
}

class CampusFloorSummary {
  const CampusFloorSummary({
    required this.floor,
    required this.label,
    required this.roomCount,
  });

  factory CampusFloorSummary.fromJson(Map<String, dynamic> json) =>
      CampusFloorSummary(
        floor: json['floor'] as int,
        label: json['label'] as String,
        roomCount: json['room_count'] as int,
      );

  final int floor;
  final String label;
  final int roomCount;
}

class CampusFloorIndex {
  const CampusFloorIndex({
    required this.provenance,
    required this.canvas,
    required this.floors,
  });

  factory CampusFloorIndex.fromJson(Map<String, dynamic> json) =>
      CampusFloorIndex(
        provenance: json['provenance'] as String,
        canvas: CampusCanvas.fromJson(json['canvas'] as Map<String, dynamic>),
        floors: (json['floors'] as List<dynamic>)
            .map(
              (item) => CampusFloorSummary.fromJson(
                item as Map<String, dynamic>,
              ),
            )
            .toList(),
      );

  final String provenance;
  final CampusCanvas canvas;
  final List<CampusFloorSummary> floors;
}

class CampusRect {
  const CampusRect({
    required this.x,
    required this.y,
    required this.width,
    required this.height,
  });

  factory CampusRect.fromJson(Map<String, dynamic> json) => CampusRect(
    x: (json['x'] as num).toDouble(),
    y: (json['y'] as num).toDouble(),
    width: (json['w'] as num).toDouble(),
    height: (json['h'] as num).toDouble(),
  );

  final double x;
  final double y;
  final double width;
  final double height;
}

class CampusCore {
  const CampusCore({required this.geometry, required this.label});

  factory CampusCore.fromJson(Map<String, dynamic> json) => CampusCore(
    geometry: CampusRect.fromJson(json),
    label: json['label'] as String,
  );

  final CampusRect geometry;
  final String label;
}

class CampusNavNode {
  const CampusNavNode({
    required this.nodeKey,
    required this.kind,
    required this.floor,
    required this.x,
    required this.y,
    required this.label,
  });

  factory CampusNavNode.fromJson(Map<String, dynamic> json) => CampusNavNode(
    nodeKey: json['node_key'] as String,
    kind: json['kind'] as String,
    floor: json['floor'] as int,
    x: (json['x'] as num).toDouble(),
    y: (json['y'] as num).toDouble(),
    label: json['label'] as String,
  );

  final String nodeKey;
  final String kind;
  final int floor;
  final double x;
  final double y;
  final String label;
}

class CampusRoomOccupancy {
  const CampusRoomOccupancy({
    required this.occupied,
    required this.sessions,
  });

  factory CampusRoomOccupancy.fromJson(Map<String, dynamic> json) =>
      CampusRoomOccupancy(
        occupied: json['occupied'] as bool,
        sessions: json['sessions'] as List<dynamic>,
      );

  final bool occupied;
  final List<dynamic> sessions;
}

class CampusFloorRoom {
  const CampusFloorRoom({
    required this.roomId,
    required this.geometry,
    required this.color,
    required this.status,
    required this.capacityEffective,
    required this.dataStatus,
    required this.realLabel,
    required this.aliases,
    required this.occupancy,
  });

  factory CampusFloorRoom.fromJson(Map<String, dynamic> json) =>
      CampusFloorRoom(
        roomId: json['room_id'] as String,
        geometry: CampusRect.fromJson(json['geometry'] as Map<String, dynamic>),
        color: json['color'] as String,
        status: json['status'] as String,
        capacityEffective: json['capacity_effective'] as int,
        dataStatus: json['data_status'] as String,
        realLabel: json['real_label'] as String,
        aliases: (json['aliases'] as List<dynamic>).cast<String>(),
        occupancy: json['occupancy'] == null
            ? null
            : CampusRoomOccupancy.fromJson(
                json['occupancy'] as Map<String, dynamic>,
              ),
      );

  final String roomId;
  final CampusRect geometry;
  final String color;
  final String status;
  final int capacityEffective;
  final String dataStatus;
  final String realLabel;
  final List<String> aliases;
  final CampusRoomOccupancy? occupancy;
}

class CampusFloorPlan {
  const CampusFloorPlan({
    required this.floor,
    required this.label,
    required this.canvas,
    required this.rooms,
    required this.cores,
    required this.navNodes,
    this.date,
    this.weekday,
    this.holiday,
  });

  factory CampusFloorPlan.fromJson(Map<String, dynamic> json) =>
      CampusFloorPlan(
        floor: json['floor'] as int,
        label: json['label'] as String,
        canvas: CampusCanvas.fromJson(json['canvas'] as Map<String, dynamic>),
        date: json['date'] as String?,
        weekday: json['weekday'] as String?,
        holiday: json['holiday'] as String?,
        cores: (json['cores'] as List<dynamic>? ?? [])
            .map((item) => CampusCore.fromJson(item as Map<String, dynamic>))
            .toList(),
        navNodes: (json['nav_nodes'] as List<dynamic>? ?? [])
            .map(
              (item) => CampusNavNode.fromJson(item as Map<String, dynamic>),
            )
            .toList(),
        rooms: (json['rooms'] as List<dynamic>)
            .map(
              (item) =>
                  CampusFloorRoom.fromJson(item as Map<String, dynamic>),
            )
            .toList(),
      );

  final int floor;
  final String label;
  final CampusCanvas canvas;
  final String? date;
  final String? weekday;
  final String? holiday;
  final List<CampusCore> cores;
  final List<CampusNavNode> navNodes;
  final List<CampusFloorRoom> rooms;
}

class CampusRoomRecord {
  const CampusRoomRecord({
    required this.number,
    required this.realLabel,
    required this.aliases,
    required this.floor,
    required this.capacity,
    required this.capacityEffective,
    required this.dataStatus,
    required this.status,
  });

  factory CampusRoomRecord.fromJson(Map<String, dynamic> json) =>
      CampusRoomRecord(
        number: json['number'] as String,
        realLabel: json['real_label'] as String,
        aliases: (json['aliases'] as List<dynamic>).cast<String>(),
        floor: json['floor'] as int,
        capacity: (json['capacity'] as num).toInt(),
        capacityEffective: (json['capacity_effective'] as num).toInt(),
        dataStatus: json['data_status'] as String,
        status: json['status'] as String,
      );

  final String number;
  final String realLabel;
  final List<String> aliases;
  final int floor;
  final int capacity;
  final int capacityEffective;
  final String dataStatus;
  final String status;

  bool matches(String query) {
    final normalized = query.trim().toLowerCase();
    if (normalized.isEmpty) return true;
    return number.toLowerCase().contains(normalized) ||
        realLabel.toLowerCase().contains(normalized) ||
        aliases.any((alias) => alias.toLowerCase().contains(normalized));
  }
}

class CampusRouteEdge {
  const CampusRouteEdge({
    required this.fromNode,
    required this.toNode,
    required this.mode,
    required this.distanceMetres,
    required this.waitSeconds,
    required this.weight,
  });

  factory CampusRouteEdge.fromJson(Map<String, dynamic> json) =>
      CampusRouteEdge(
        fromNode: json['from'] as String,
        toNode: json['to'] as String,
        mode: json['mode'] as String,
        distanceMetres: (json['distance_m'] as num).toDouble(),
        waitSeconds: (json['wait_seconds'] as num).toDouble(),
        weight: (json['weight'] as num).toDouble(),
      );

  final String fromNode;
  final String toNode;
  final String mode;
  final double distanceMetres;
  final double waitSeconds;
  final double weight;
}

class CampusRouteNode {
  const CampusRouteNode({
    required this.nodeKey,
    required this.floor,
    required this.x,
    required this.y,
    required this.kind,
    required this.label,
  });

  factory CampusRouteNode.fromJson(Map<String, dynamic> json) =>
      CampusRouteNode(
        nodeKey: json['node_key'] as String,
        floor: json['floor'] as int,
        x: (json['x'] as num).toDouble(),
        y: (json['y'] as num).toDouble(),
        kind: json['kind'] as String,
        label: json['label'] as String,
      );

  final String nodeKey;
  final int floor;
  final double x;
  final double y;
  final String kind;
  final String label;
}

class CampusRouteStep {
  const CampusRouteStep({
    required this.instruction,
    required this.floor,
    required this.fromNode,
    required this.toNode,
    required this.distanceMetres,
    required this.kind,
  });

  factory CampusRouteStep.fromJson(Map<String, dynamic> json) =>
      CampusRouteStep(
        instruction: json['instruction'] as String,
        floor: json['floor'] as int,
        fromNode: json['from_node'] as String,
        toNode: json['to_node'] as String,
        distanceMetres: (json['distance_m'] as num).toDouble(),
        kind: json['kind'] as String,
      );

  final String instruction;
  final int floor;
  final String fromNode;
  final String toNode;
  final double distanceMetres;
  final String kind;
}

class CampusRoute {
  const CampusRoute({
    required this.fromRoom,
    required this.toRoom,
    required this.mode,
    required this.nodeKeys,
    required this.edges,
    required this.distanceMetres,
    required this.routeCostSeconds,
    required this.provenance,
    required this.path,
    required this.steps,
    required this.floorsVisited,
  });

  factory CampusRoute.fromJson(Map<String, dynamic> json) => CampusRoute(
    fromRoom: json['from_room'] as String,
    toRoom: json['to_room'] as String,
    mode: json['mode'] as String,
    nodeKeys: (json['node_keys'] as List<dynamic>).cast<String>(),
    edges: (json['edges'] as List<dynamic>)
        .map((item) => CampusRouteEdge.fromJson(item as Map<String, dynamic>))
        .toList(),
    distanceMetres: (json['distance_m'] as num).toDouble(),
    routeCostSeconds: (json['route_cost_seconds'] as num).toDouble(),
    provenance: json['provenance'] as String,
    path: (json['path'] as List<dynamic>)
        .map((item) => CampusRouteNode.fromJson(item as Map<String, dynamic>))
        .toList(),
    steps: (json['steps'] as List<dynamic>)
        .map((item) => CampusRouteStep.fromJson(item as Map<String, dynamic>))
        .toList(),
    floorsVisited: (json['floors_visited'] as List<dynamic>).cast<int>(),
  );

  final String fromRoom;
  final String toRoom;
  final String mode;
  final List<String> nodeKeys;
  final List<CampusRouteEdge> edges;
  final double distanceMetres;
  final double routeCostSeconds;
  final String provenance;
  final List<CampusRouteNode> path;
  final List<CampusRouteStep> steps;
  final List<int> floorsVisited;
}
