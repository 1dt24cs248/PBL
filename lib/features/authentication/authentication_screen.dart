import 'package:dio/dio.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../core/storage/secure_storage.dart';

class AppUser {
  const AppUser({
    required this.id,
    required this.username,
    required this.fullName,
    required this.role,
    required this.category,
    required this.department,
  });

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
    id: json['id'] as int,
    username: json['username'] as String,
    fullName: json['full_name'] as String,
    role: json['role'] as String,
    category: json['category'] as String,
    department: json['department'] as String? ?? '',
  );

  final int id;
  final String username;
  final String fullName;
  final String role;
  final String category;
  final String department;
}

class AuthNotifier extends AsyncNotifier<AppUser?> {
  ApiClient get _api => ref.read(apiClientProvider);
  SecureTokenStorage get _storage => ref.read(secureTokenStorageProvider);

  @override
  Future<AppUser?> build() async {
    final token = await _storage.readToken();
    if (token == null || token.isEmpty) return null;
    return _loadMe();
  }

  Future<AppUser?> _loadMe() async {
    final response = await _api.dio.get<Map<String, dynamic>>('/auth/me');
    return AppUser.fromJson(response.data!);
  }

  Future<void> login(String username, String password) async {
    state = const AsyncLoading();
    try {
      final response = await _api.dio.post<Map<String, dynamic>>(
        '/auth/login',
        data: {'username': username, 'password': password},
      );
      final data = response.data!;
      await _storage.writeToken(data['access_token'] as String);
      state = AsyncData(await _loadMe());
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      rethrow;
    }
  }

  Future<void> logout() async {
    await _storage.clearToken();
    state = const AsyncData(null);
  }

  void handleUnauthorized() {
    state = const AsyncData(null);
  }
}

final authProvider = AsyncNotifierProvider<AuthNotifier, AppUser?>(
  AuthNotifier.new,
);

class AuthenticationScreen extends ConsumerStatefulWidget {
  const AuthenticationScreen({super.key});

  @override
  ConsumerState<AuthenticationScreen> createState() =>
      _AuthenticationScreenState();
}

class _AuthenticationScreenState extends ConsumerState<AuthenticationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    try {
      await ref
          .read(authProvider.notifier)
          .login(_usernameController.text.trim(), _passwordController.text);
    } on DioException catch (error) {
      final data = error.response?.data;
      final detail = data is Map<String, dynamic>
          ? data['detail']?.toString()
          : data is String && data.isNotEmpty
          ? data
          : error.message;
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(detail ?? 'Login failed')));
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Login failed: $error')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final loading = auth.isLoading;
    return Scaffold(
      appBar: AppBar(title: const Text('PBL Campus')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Sign in',
                    style: Theme.of(context).textTheme.headlineMedium,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  TextFormField(
                    key: const Key('username_field'),
                    controller: _usernameController,
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(
                      labelText: 'Username or USN',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                    validator: (value) => value == null || value.trim().isEmpty
                        ? 'Enter your username or USN'
                        : null,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    key: const Key('password_field'),
                    controller: _passwordController,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: 'Password',
                      prefixIcon: Icon(Icons.lock_outline),
                    ),
                    validator: (value) => value == null || value.isEmpty
                        ? 'Enter your password'
                        : null,
                    onFieldSubmitted: (_) => _submit(),
                  ),
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: loading ? null : _submit,
                    child: loading
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Login'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
