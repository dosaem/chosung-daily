/// 빌드 때 주입하는 값들. `--dart-define=API_BASE_URL=https://...` 형태로 넘기고
/// (티켓 32 의 워크플로), 안 넘기면 로컬 개발 기본값을 쓴다.
abstract final class AppEnv {
  /// 로컬 개발 기본값은 Android 에뮬레이터에서 호스트를 가리키는 주소다.
  /// iOS 시뮬레이터·실기기는 `--dart-define` 으로 덮는다.
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8089/api/v1',
  );

  /// 비어 있으면 Sentry 를 초기화하지 않는다(개발·CI 기본).
  static const sentryDsn = String.fromEnvironment('SENTRY_DSN');
}
