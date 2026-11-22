import 'package:dio/dio.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/config/app_config.dart';

class AuthCategoryMismatch implements Exception {
  const AuthCategoryMismatch(this.category);

  final String category;
}

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

  Future<AppUser> _loadMe() async {
    final response = await _api.dio.get<Map<String, dynamic>>('/auth/me');
    return AppUser.fromJson(response.data!);
  }

  Future<void> login(
    String username,
    String password, {
    required String selectedCategory,
  }) async {
    state = const AsyncLoading();
    try {
      final response = await _api.dio.post<Map<String, dynamic>>(
        '/auth/login',
        data: {'username': username, 'password': password},
      );
      final data = response.data!;
      await _storage.writeToken(data['access_token'] as String);
      final user = await _loadMe();
      if (user.category != selectedCategory) {
        await _storage.clearToken();
        state = const AsyncData(null);
        throw AuthCategoryMismatch(user.category);
      }
      state = AsyncData(user);
    } catch (error, stackTrace) {
      if (error is AuthCategoryMismatch) rethrow;
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
  String? _selectedCategory;
  String? _categoryMessage;
  String? _roleValidationMessage;
  bool _showPassword = false;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _categoryMessage = null;
      _roleValidationMessage = _selectedCategory == null
          ? 'Select your role to continue.'
          : null;
    });
    final isValid = _formKey.currentState!.validate();
    if (!isValid || _selectedCategory == null) return;
    try {
      await ref
          .read(authProvider.notifier)
          .login(
            _usernameController.text.trim(),
            _passwordController.text,
            selectedCategory: _selectedCategory!,
          );
    } on AuthCategoryMismatch catch (error) {
      if (mounted) {
        setState(() {
          _categoryMessage =
              'This account belongs to the ${error.category} category. '
              'Please select ${error.category}.';
        });
      }
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
      appBar: AppBar(title: const Text('DSATM Smart Campus')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Center(
                    child: Image.asset(
                      'assets/images/dsatm_logo.png',
                      width: 64,
                      height: 64,
                      errorBuilder: (_, _, _) => const CircleAvatar(
                        radius: 31,
                        backgroundColor: Color(0xFF14B8A6),
                        child: Icon(
                          Icons.school_outlined,
                          size: 34,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'DSATM Smart Campus',
                    style: Theme.of(context).textTheme.headlineSmall,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'PBL Campus Management (student project prototype)',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  Text('Role', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final category in const [
                        'Student',
                        'Faculty',
                        'Management',
                      ])
                        ChoiceChip(
                          key: Key('role_$category'),
                          label: Text(category),
                          selected: _selectedCategory == category,
                          onSelected: (_) => setState(() {
                            _selectedCategory = category;
                            _categoryMessage = null;
                            _roleValidationMessage = null;
                          }),
                        ),
                    ],
                  ),
                  if (_categoryMessage != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        _categoryMessage!,
                        key: const Key('category_mismatch_message'),
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ),
                  if (_roleValidationMessage != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        _roleValidationMessage!,
                        key: const Key('role_validation_message'),
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ),
                  const SizedBox(height: 12),
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
                  const SizedBox(height: 12),
                  TextFormField(
                    key: const Key('password_field'),
                    controller: _passwordController,
                    obscureText: !_showPassword,
                    decoration: InputDecoration(
                      labelText: 'Password',
                      prefixIcon: const Icon(Icons.lock_outline),
                      suffixIcon: IconButton(
                        key: const Key('password_visibility_toggle'),
                        tooltip: _showPassword
                            ? 'Hide password'
                            : 'Show password',
                        onPressed: () =>
                            setState(() => _showPassword = !_showPassword),
                        icon: Icon(
                          _showPassword
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined,
                        ),
                      ),
                    ),
                    validator: (value) => value == null || value.isEmpty
                        ? 'Enter your password'
                        : null,
                    onFieldSubmitted: (_) => _submit(),
                  ),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      key: const Key('forgot_password'),
                      onPressed: _showPasswordHelp,
                      style: TextButton.styleFrom(
                        minimumSize: const Size(0, 32),
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        visualDensity: VisualDensity.compact,
                      ),
                      child: const Text('Forgot Password?'),
                    ),
                  ),
                  const SizedBox(height: 12),
                  FilledButton(
                    key: const Key('login_button'),
                    onPressed: loading ? null : _submit,
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(44),
                    ),
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

  Future<void> _showPasswordHelp() => showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('Forgot Password?'),
      content: const Text(AppConfig.passwordHelpText),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Close'),
        ),
      ],
    ),
  );
}
