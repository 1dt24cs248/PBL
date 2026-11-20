import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureTokenStorage {
  SecureTokenStorage({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  static const tokenKey = 'access_token';
  final FlutterSecureStorage _storage;

  Future<String?> readToken() => _storage.read(key: tokenKey);

  Future<void> writeToken(String token) =>
      _storage.write(key: tokenKey, value: token);

  Future<void> clearToken() => _storage.delete(key: tokenKey);
}

final secureTokenStorageProvider = Provider<SecureTokenStorage>(
  (ref) => SecureTokenStorage(),
);
