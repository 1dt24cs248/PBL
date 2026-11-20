import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/app_config.dart';
import '../storage/secure_storage.dart';
import '../../features/authentication/authentication_screen.dart';

class ApiClient {
  ApiClient({
    required AppConfig config,
    required this._storage,
    this.onUnauthorized,
  }) : dio = Dio(
         BaseOptions(
           baseUrl: config.baseUrl,
           connectTimeout: const Duration(seconds: 15),
           receiveTimeout: const Duration(seconds: 15),
           headers: const {'Accept': 'application/json'},
         ),
       ) {
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _storage.readToken();
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode == 401) {
            await _storage.clearToken();
            onUnauthorized?.call();
          }
          handler.next(error);
        },
      ),
    );
  }

  final Dio dio;
  final SecureTokenStorage _storage;
  final void Function()? onUnauthorized;
}

final appConfigProvider = Provider<AppConfig>(
  (_) => AppConfig.fromEnvironment(),
);

final apiClientProvider = Provider<ApiClient>((ref) {
  final storage = ref.watch(secureTokenStorageProvider);
  final config = ref.watch(appConfigProvider);
  return ApiClient(
    config: config,
    storage: storage,
    onUnauthorized: () {
      ref.read(authProvider.notifier).handleUnauthorized();
    },
  );
});
