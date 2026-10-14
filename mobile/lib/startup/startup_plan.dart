import 'package:chosung/api/api_models.dart';
import 'package:chosung/startup/app_version.dart';
import 'package:flutter/foundation.dart';

enum StartupDestination { maintenance, updateRequired, home }

@immutable
class StartupPlan {
  const StartupPlan._(
    this.destination, {
    this.maintenanceMessage,
    this.storeUrl,
  });

  final StartupDestination destination;
  final String? maintenanceMessage;
  final String? storeUrl;
}

/// `/config` 와 설치된 앱 버전만 보고 첫 화면을 고른다(S7 분기).
///
/// 점검이 업데이트보다 먼저다 — 점검 중에는 최신 버전으로 올려도 쓸 수 없으니
/// 스토어로 보내는 건 헛걸음이다.
StartupPlan planStartup({
  required AppConfig config,
  required String appVersion,
  required bool isIos,
}) {
  if (config.maintenance.enabled) {
    return StartupPlan._(
      StartupDestination.maintenance,
      maintenanceMessage: config.maintenance.message,
    );
  }

  final minimum = isIos
      ? config.minAppVersion.ios
      : config.minAppVersion.android;
  if (isUpdateRequired(current: appVersion, minimum: minimum)) {
    return StartupPlan._(
      StartupDestination.updateRequired,
      // 스토어 등록 전에는 null 이다 — 화면이 버튼 없이 안내만 띄운다.
      storeUrl: isIos ? config.storeUrls.ios : config.storeUrls.android,
    );
  }

  return const StartupPlan._(StartupDestination.home);
}
