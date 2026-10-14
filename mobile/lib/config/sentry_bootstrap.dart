import 'package:flutter/foundation.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

/// Sentry 로 앱을 감싸 띄운다. DSN 이 비어 있으면(개발·CI) 그냥 띄운다 —
/// 로컬에서 만든 예외가 운영 이슈 목록에 섞이지 않게 한다.
Future<void> runWithSentry({
  required String dsn,
  required void Function() runApp,
  Future<void> Function(String dsn, void Function() runApp)? initialize,
}) async {
  if (dsn.isEmpty) {
    runApp();
    return;
  }
  await (initialize ?? _initSentry)(dsn, runApp);
}

Future<void> _initSentry(String dsn, void Function() runApp) =>
    SentryFlutter.init(
      (options) => options
        ..dsn = dsn
        // 백엔드(티켓 08)와 같은 기준: 개인정보를 붙이지 않는다.
        ..sendDefaultPii = false
        ..environment = kReleaseMode ? 'production' : 'development',
      appRunner: runApp,
    );
