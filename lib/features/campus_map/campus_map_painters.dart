import 'package:flutter/gestures.dart' show kTouchSlop;
import 'package:material_ui/material_ui.dart';

import 'campus_map_models.dart';
import 'isometric_transform.dart';

Color campusApiColor(String value) {
  if (!RegExp(r'^#[0-9A-Fa-f]{6}$').hasMatch(value)) {
    throw FormatException('Expected an API color in #RRGGBB format.', value);
  }
  return Color(0xFF000000 | int.parse(value.substring(1), radix: 16));
}

CampusFloorRoom? hitTestCampusRoom(
  List<CampusFloorRoom> rooms,
  Offset canvasPoint,
) {
  for (final room in rooms.reversed) {
    final geometry = room.geometry;
    if (Rect.fromLTWH(
      geometry.x,
      geometry.y,
      geometry.width,
      geometry.height,
    ).contains(canvasPoint)) {
      return room;
    }
  }
  return null;
}

List<Offset> routePolylineForFloor(CampusRoute route, int floor) => [
  for (final node in route.path)
    if (node.floor == floor) Offset(node.x, node.y),
];

class CampusFloorMapView extends StatefulWidget {
  const CampusFloorMapView({
    super.key,
    required this.plan,
    required this.onRoomTap,
  });

  final CampusFloorPlan plan;
  final ValueChanged<CampusFloorRoom> onRoomTap;

  @override
  State<CampusFloorMapView> createState() => _CampusFloorMapViewState();
}

class _CampusFloorMapViewState extends State<CampusFloorMapView> {
  final _transformationController = TransformationController();
  final Set<int> _activePointers = {};
  Offset? _tapDownPosition;

  @override
  void didUpdateWidget(covariant CampusFloorMapView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.plan.floor != widget.plan.floor) {
      _transformationController.value = Matrix4.identity();
    }
  }

  @override
  void dispose() {
    _transformationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final width = constraints.maxWidth;
      final height =
          width * widget.plan.canvas.height / widget.plan.canvas.width;
      final displaySize = Size(width, height);
      return SizedBox(
        key: const Key('campus_floor_canvas'),
        width: width,
        height: height,
        child: Listener(
          onPointerDown: (event) {
            if (_activePointers.isEmpty) {
              _tapDownPosition = event.localPosition;
            } else {
              _tapDownPosition = null;
            }
            _activePointers.add(event.pointer);
          },
          onPointerCancel: (event) {
            _activePointers.remove(event.pointer);
            _tapDownPosition = null;
          },
          onPointerUp: (event) {
            final start = _tapDownPosition;
            final isTap =
                _activePointers.length == 1 &&
                start != null &&
                (event.localPosition - start).distance <= kTouchSlop;
            _activePointers.remove(event.pointer);
            if (isTap) {
              final scenePoint = _transformationController.toScene(
                event.localPosition,
              );
              final canvasPoint = Offset(
                scenePoint.dx * widget.plan.canvas.width / displaySize.width,
                scenePoint.dy * widget.plan.canvas.height / displaySize.height,
              );
              final room = hitTestCampusRoom(widget.plan.rooms, canvasPoint);
              if (room != null) widget.onRoomTap(room);
            }
            if (_activePointers.isEmpty) _tapDownPosition = null;
          },
          child: InteractiveViewer(
            transformationController: _transformationController,
            constrained: false,
            alignment: Alignment.topLeft,
            minScale: 1,
            maxScale: 4,
            child: CustomPaint(
              size: displaySize,
              painter: CampusFloorMapPainter(plan: widget.plan),
            ),
          ),
        ),
      );
    },
  );
}

class CampusFloorMapPainter extends CustomPainter {
  const CampusFloorMapPainter({required this.plan});

  final CampusFloorPlan plan;

  @override
  void paint(Canvas canvas, Size size) {
    final scaleX = size.width / plan.canvas.width;
    final scaleY = size.height / plan.canvas.height;
    canvas.save();
    canvas.scale(scaleX, scaleY);
    canvas.drawRect(
      Rect.fromLTWH(0, 0, plan.canvas.width, plan.canvas.height),
      Paint()..color = const Color(0xFFF8FAFC),
    );
    canvas.drawRect(
      Rect.fromLTWH(0, 270, plan.canvas.width, 60),
      Paint()..color = const Color(0xFFE2E8F0),
    );
    _drawLabel(
      canvas,
      'Central corridor',
      const Offset(420, 294),
      const TextStyle(
        color: Color(0xFF334155),
        fontSize: 24,
        fontWeight: FontWeight.w600,
      ),
    );

    for (final core in plan.cores) {
      final geometry = core.geometry;
      final rect = Rect.fromLTWH(
        geometry.x,
        geometry.y,
        geometry.width,
        geometry.height,
      );
      canvas.drawRect(rect, Paint()..color = const Color(0xFF64748B));
      _drawLabel(
        canvas,
        core.label,
        Offset(rect.left + 4, rect.center.dy - 8),
        const TextStyle(
          color: Colors.white,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
      );
    }

    for (final room in plan.rooms) {
      final geometry = room.geometry;
      final rect = Rect.fromLTWH(
        geometry.x,
        geometry.y,
        geometry.width,
        geometry.height,
      );
      canvas.drawRect(rect, Paint()..color = campusApiColor(room.color));
      final overlay = _roomOverlay(room);
      canvas.drawRect(
        rect,
        Paint()
          ..color = overlay.withValues(alpha: 0.18)
          ..style = PaintingStyle.fill,
      );
      canvas.drawRect(
        rect,
        Paint()
          ..color = overlay
          ..style = PaintingStyle.stroke
          ..strokeWidth = 5,
      );
      canvas.drawRect(
        Rect.fromLTWH(rect.left, rect.top, rect.width, 12),
        Paint()..color = overlay,
      );
      _drawLabel(
        canvas,
        room.roomId,
        Offset(rect.left + 5, rect.top + 17),
        const TextStyle(
          color: Color(0xFF0F172A),
          fontSize: 24,
          fontWeight: FontWeight.w600,
        ),
        maxWidth: rect.width - 10,
      );
    }
    canvas.restore();
  }

  Color _roomOverlay(CampusFloorRoom room) {
    if (room.status == 'under_maintenance') return const Color(0xFFB91C1C);
    if (room.occupancy?.occupied == true) return const Color(0xFFEA580C);
    if (room.status == 'available') return const Color(0xFF15803D);
    return const Color(0xFF64748B);
  }

  void _drawLabel(
    Canvas canvas,
    String text,
    Offset offset,
    TextStyle style, {
    double? maxWidth,
  }) {
    final painter = TextPainter(
      text: TextSpan(text: text, style: style),
      textDirection: TextDirection.ltr,
      maxLines: 1,
      ellipsis: '…',
    )..layout(maxWidth: maxWidth ?? plan.canvas.width);
    painter.paint(canvas, offset);
  }

  @override
  bool shouldRepaint(covariant CampusFloorMapPainter oldDelegate) =>
      oldDelegate.plan != plan;
}

class CampusRouteFloorMap extends StatelessWidget {
  const CampusRouteFloorMap({
    super.key,
    required this.route,
    required this.floor,
  });

  final CampusRoute route;
  final int floor;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final width = constraints.maxWidth;
      final height = width * 0.6;
      return SizedBox(
        width: width,
        height: height,
        child: InteractiveViewer(
          minScale: 1,
          maxScale: 4,
          child: CustomPaint(
            size: Size(width, height),
            painter: CampusRouteFloorPainter(route: route, floor: floor),
          ),
        ),
      );
    },
  );
}

class CampusRouteFloorPainter extends CustomPainter {
  const CampusRouteFloorPainter({required this.route, required this.floor});

  final CampusRoute route;
  final int floor;

  @override
  void paint(Canvas canvas, Size size) {
    const canvasWidth = 1000.0;
    const canvasHeight = 600.0;
    canvas.save();
    canvas.scale(size.width / canvasWidth, size.height / canvasHeight);
    canvas.drawRect(
      const Rect.fromLTWH(0, 0, canvasWidth, canvasHeight),
      Paint()..color = const Color(0xFFF8FAFC),
    );
    canvas.drawRect(
      const Rect.fromLTWH(0, 270, canvasWidth, 60),
      Paint()..color = const Color(0xFFE2E8F0),
    );

    final nodes = route.path.where((node) => node.floor == floor).toList();
    if (nodes.length > 1) {
      final path = Path()..moveTo(nodes.first.x, nodes.first.y);
      for (final node in nodes.skip(1)) {
        path.lineTo(node.x, node.y);
      }
      canvas.drawPath(
        path,
        Paint()
          ..color = const Color(0xFF2563EB)
          ..strokeWidth = 8
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round
          ..style = PaintingStyle.stroke,
      );
    }

    for (final node in nodes) {
      final point = Offset(node.x, node.y);
      final isStart = identical(node, route.path.first);
      final isEnd = identical(node, route.path.last);
      final isStairs = node.kind.toLowerCase().contains('stair');
      final isLift = node.kind.toLowerCase().contains('lift');
      if (isStart) {
        canvas.drawCircle(point, 18, Paint()..color = const Color(0xFF1D4ED8));
      }
      if (isEnd) {
        canvas.drawCircle(
          point,
          isStart ? 11 : 18,
          Paint()..color = const Color(0xFF15803D),
        );
      }
      if (isStairs || isLift) {
        canvas.drawCircle(
          point,
          12,
          Paint()
            ..color = isStairs
                ? const Color(0xFFB45309)
                : const Color(0xFF7C3AED),
        );
        _drawLabel(
          canvas,
          isStairs ? 'Stairs' : 'Lift',
          Offset(point.dx + 12, point.dy - 28),
          const TextStyle(
            color: Color(0xFF0F172A),
            fontSize: 24,
            fontWeight: FontWeight.w600,
          ),
        );
      }
    }
    canvas.restore();
  }

  void _drawLabel(Canvas canvas, String text, Offset offset, TextStyle style) {
    final painter = TextPainter(
      text: TextSpan(text: text, style: style),
      textDirection: TextDirection.ltr,
    )..layout();
    painter.paint(canvas, offset);
  }

  @override
  bool shouldRepaint(covariant CampusRouteFloorPainter oldDelegate) =>
      oldDelegate.route != route || oldDelegate.floor != floor;
}

class CampusIsometricMapView extends StatelessWidget {
  const CampusIsometricMapView({
    super.key,
    required this.plan,
    required this.onRoomTap,
    this.energyByRoom = const {},
  });

  final CampusFloorPlan plan;
  final ValueChanged<CampusFloorRoom> onRoomTap;
  final Map<String, double> energyByRoom;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final width = constraints.maxWidth;
      const transform = IsometricTransform();
      return SizedBox(
        key: const Key('campus_isometric_canvas'),
        width: width,
        height: width * 0.6,
        child: GestureDetector(
          onTapUp: (details) {
            final inverse = transform.toPlan(
              details.localPosition,
              floor: plan.floor,
            );
            final room = hitTestCampusRoom(plan.rooms, inverse);
            if (room != null) onRoomTap(room);
          },
          child: CustomPaint(
            size: Size(width, width * 0.6),
            painter: CampusIsometricPainter(
              plan: plan,
              transform: transform,
              reduceEffects: false,
              energyByRoom: energyByRoom,
            ),
          ),
        ),
      );
    },
  );
}

class CampusIsometricPainter extends CustomPainter {
  const CampusIsometricPainter({
    required this.plan,
    required this.transform,
    required this.reduceEffects,
    this.energyByRoom = const {},
  });

  final CampusFloorPlan plan;
  final IsometricTransform transform;
  final bool reduceEffects;
  final Map<String, double> energyByRoom;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(
      Offset.zero & size,
      Paint()..color = const Color(0xFF0B1120),
    );

    final gridPaint = Paint()
      ..color = const Color(0xFF1E293B)
      ..strokeWidth = 1;
    for (var x = 0.0; x < size.width; x += 32) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (var y = 0.0; y < size.height; y += 32) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    for (final room in plan.rooms) {
      final geometry = room.geometry;
      final leftTop = transform.toScreen(
        Offset(geometry.x, geometry.y),
        floor: plan.floor,
      );
      final rightTop = transform.toScreen(
        Offset(geometry.x + geometry.width, geometry.y),
        floor: plan.floor,
      );
      final rightBottom = transform.toScreen(
        Offset(geometry.x + geometry.width, geometry.y + geometry.height),
        floor: plan.floor,
      );
      final leftBottom = transform.toScreen(
        Offset(geometry.x, geometry.y + geometry.height),
        floor: plan.floor,
      );
      final statusColor = _statusColor(room);
      const extrusion = 12.0;

      final top = Path()
        ..moveTo(leftTop.dx, leftTop.dy)
        ..lineTo(rightTop.dx, rightTop.dy)
        ..lineTo(rightBottom.dx, rightBottom.dy)
        ..lineTo(leftBottom.dx, leftBottom.dy)
        ..close();

      canvas.drawPath(
        top,
        Paint()..color = statusColor.withValues(alpha: 0.82),
      );
      canvas.drawPath(
        top,
        Paint()
          ..color = reduceEffects
              ? statusColor
              : statusColor.withValues(alpha: 0.9)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1,
      );

      final rightSide = Path()
        ..moveTo(rightTop.dx, rightTop.dy)
        ..lineTo(rightBottom.dx, rightBottom.dy)
        ..lineTo(rightBottom.dx, rightBottom.dy + extrusion)
        ..lineTo(rightTop.dx, rightTop.dy + extrusion)
        ..close();
      canvas.drawPath(
        rightSide,
        Paint()..color = statusColor.withValues(alpha: 0.48),
      );

      final bottomSide = Path()
        ..moveTo(leftBottom.dx, leftBottom.dy)
        ..lineTo(rightBottom.dx, rightBottom.dy)
        ..lineTo(rightBottom.dx, rightBottom.dy + extrusion)
        ..lineTo(leftBottom.dx, leftBottom.dy + extrusion)
        ..close();
      canvas.drawPath(
        bottomSide,
        Paint()..color = statusColor.withValues(alpha: 0.30),
      );

      final label = TextPainter(
        text: TextSpan(
          text: room.roomId,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      label.paint(
        canvas,
        Offset(
          (leftTop.dx + rightBottom.dx) / 2 - label.width / 2,
          (leftTop.dy + rightBottom.dy) / 2 - label.height / 2,
        ),
      );
    }

    for (final core in plan.cores) {
      final point = transform.toScreen(
        Offset(core.geometry.x, core.geometry.y),
        floor: plan.floor,
      );
      canvas.drawCircle(
        point,
        8,
        Paint()
          ..color = const Color(0xFF64748B)
          ..strokeWidth = 2
          ..style = PaintingStyle.stroke,
      );
    }
  }

  Color _statusColor(CampusFloorRoom room) {
    final kwh = energyByRoom[room.roomId];
    if (kwh != null) {
      if (kwh >= 20) return const Color(0xFFDC2626);
      if (kwh >= 10) return const Color(0xFFF59E0B);
      return const Color(0xFF14B8A6);
    }
    if (room.status == 'under_maintenance') return const Color(0xFFEF4444);
    if (room.status == 'temporarily_unavailable') {
      return const Color(0xFF64748B);
    }
    if (room.occupancy?.occupied == true) return const Color(0xFFF59E0B);
    if (room.status == 'available') return const Color(0xFF10B981);
    return const Color(0xFF64748B);
  }

  @override
  bool shouldRepaint(covariant CampusIsometricPainter oldDelegate) =>
      oldDelegate.plan != plan ||
      oldDelegate.transform != transform ||
      oldDelegate.reduceEffects != reduceEffects;
}
