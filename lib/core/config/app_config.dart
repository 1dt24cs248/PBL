class AppConfig {
  const AppConfig({this.baseUrl = defaultBaseUrl});

  static const defaultBaseUrl = 'http://10.0.2.2:8000';
  static const passwordHelpText =
      'This demo build has no self-service password reset. '
      'Please contact your department office or the IT cell.';

  factory AppConfig.fromEnvironment() {
    const configuredUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: defaultBaseUrl,
    );
    return AppConfig(baseUrl: configuredUrl);
  }

  final String baseUrl;
}
