import 'package:chosung/api/api_client.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/dio_api_client.dart';
import 'package:chosung/config/app_env.dart';
import 'package:chosung/guest/guest_token_provider.dart';
import 'package:chosung/startup/app_version.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Dio 구현을 쓴다. 테스트는 `FakeApiClient` 로 이 provider 를 덮는다.
///
/// 토큰은 [guestTokenProvider] 에서 **매 요청마다** 읽는다 — 그래서 티켓 27 이
/// 토큰을 교체해도 ApiClient 를 다시 만들 필요가 없다.
final apiClientProvider = Provider<ApiClient>(
  (ref) => DioApiClient.withBaseUrl(
    baseUrl: AppEnv.apiBaseUrl,
    readToken: () => ref.read(guestTokenProvider).value,
  ),
);

/// 설치된 앱 버전. `/config` 의 `min_app_version` 과 비교한다.
final appVersionProvider = FutureProvider<String>(
  (ref) => installedAppVersion(),
);

/// 최소 버전·스토어 링크는 플랫폼마다 다르다.
final isIosProvider = Provider<bool>(
  (ref) => defaultTargetPlatform == TargetPlatform.iOS,
);

/// 첫 게스트를 발급할 때 보낼 `puzzle_language`. 기기 언어가 en 이면 en.
final devicePuzzleLanguageProvider = Provider<PuzzleLanguage>(
  (ref) => PuzzleLanguage.forDeviceLanguage(
    PlatformDispatcher.instance.locale.languageCode,
  ),
);
