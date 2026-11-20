import 'package:material_ui/material_ui.dart';

ThemeData get lightTheme => ThemeData(
  useMaterial3: true,
  colorScheme: ColorScheme.fromSeed(
    seedColor: const Color(0xFF3559A6),
    brightness: Brightness.light,
  ),
  scaffoldBackgroundColor: const Color(0xFFF7F9FC),
  inputDecorationTheme: const InputDecorationTheme(
    border: OutlineInputBorder(),
  ),
);
