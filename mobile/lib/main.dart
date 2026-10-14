import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/app_env.dart';
import 'package:chosung/config/firebase_bootstrap.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/config/sentry_bootstrap.dart';
import 'package:chosung/l10n/localization_bootstrap.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

Future<void> main() => bootstrapChosungApp();

/// main 본문을 함수로 빼둔 이유는 **시작 순서 자체가 회귀 대상**이기 때문이다 —
/// 국제화 초기화를 빼먹으면 위젯 테스트는 다 통과하는데(테스트는 언어를
/// 고정한다) 실제 앱은 첫 프레임에서 죽는다.
@visibleForTesting
Future<void> bootstrapChosungApp({
  Future<FirebaseBootstrap> Function() initializeFirebaseFn =
      initializeFirebase,
  Future<void> Function() initializeLocalizationFn = initializeLocalization,
  void Function(Widget app) start = runApp,
}) async {
  WidgetsFlutterBinding.ensureInitialized();
  // Firebase 가 떴는지는 분석 서비스를 고르는 입력이다(티켓 26) — 설정 파일이
  // 없는 빌드는 no-op 구현으로 돌아간다.
  final firebase = await initializeFirebaseFn();
  await initializeLocalizationFn();

  await runWithSentry(
    dsn: AppEnv.sentryDsn,
    runApp: () => start(
      ProviderScope(
        retry: noAutoRetry,
        overrides: [firebaseBootstrapProvider.overrideWithValue(firebase)],
        child: const AppLocalizationScope(child: ChosungApp()),
      ),
    ),
  );
}
