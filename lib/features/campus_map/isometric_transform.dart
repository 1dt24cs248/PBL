import 'dart:math' as math;

import 'package:material_ui/material_ui.dart';

class IsometricTransform {
  const IsometricTransform({
    this.scale = 0.34,
    this.origin = const Offset(500, 280),
    this.floorGap = 26,
  });

  final double scale;
  final Offset origin;
  final double floorGap;

  Offset toScreen(Offset planPoint, {required int floor}) {
    final cos30 = math.cos(math.pi / 6);
    final sin30 = math.sin(math.pi / 6);
    return Offset(
      origin.dx + (planPoint.dx - planPoint.dy) * cos30 * scale,
      origin.dy +
          (planPoint.dx + planPoint.dy) * sin30 * scale -
          floor * floorGap,
    );
  }

  Offset toPlan(Offset screenPoint, {required int floor}) {
    final cos30 = math.cos(math.pi / 6);
    final sin30 = math.sin(math.pi / 6);
    final translated = Offset(
      screenPoint.dx - origin.dx,
      screenPoint.dy - origin.dy + floor * floorGap,
    );
    final x = translated.dx / (cos30 * scale);
    final y = translated.dy / (sin30 * scale);
    return Offset((x + y) / 2, (y - x) / 2);
  }

  Offset roundTrip(Offset planPoint, {required int floor}) =>
      toPlan(toScreen(planPoint, floor: floor), floor: floor);
}
