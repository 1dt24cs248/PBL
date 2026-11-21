import 'package:material_ui/material_ui.dart';

class AppColors {
  static const appBar = Color(0xFF000000);
  static const page = Color(0xFFF0F0F0);
  static const primary = Color(0xFF14B8A6);
  static const holiday = Color(0xFF1ABC9C);
  static const lectureBackground = Color(0xFFD9F3F5);
  static const lectureText = Color(0xFF0F8A94);
  static const labBackground = Color(0xFFFBD5DC);
  static const labText = Color(0xFFD6336C);
  static const activityBackground = Color(0xFFE5E7EB);
  static const activityText = Color(0xFF4B5563);
  static const recessBackground = Color(0xFFFBF8D2);
  static const recessText = Color(0xFFE6B800);
  static const success = Color(0xFF16A34A);
  static const warning = Color(0xFFF59E0B);
  static const danger = Color(0xFFDC2626);
  static const darkHeaderStart = Color(0xFF0B1120);
  static const darkHeaderEnd = Color(0xFF111827);
}

ThemeData get lightTheme => ThemeData(
  useMaterial3: true,
  colorScheme: ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    brightness: Brightness.light,
  ),
  scaffoldBackgroundColor: AppColors.page,
  appBarTheme: const AppBarTheme(
    backgroundColor: AppColors.appBar,
    foregroundColor: Colors.white,
    elevation: 0,
  ),
  cardTheme: CardThemeData(
    color: Colors.white,
    elevation: 1,
    margin: EdgeInsets.zero,
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    shadowColor: Colors.black12,
  ),
  inputDecorationTheme: const InputDecorationTheme(
    border: OutlineInputBorder(),
    filled: true,
    fillColor: Colors.white,
  ),
  chipTheme: ChipThemeData(
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
  ),
);
