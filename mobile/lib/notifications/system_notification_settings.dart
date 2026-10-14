import 'package:app_settings/app_settings.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// OS 의 앱 알림 설정 화면을 연다(S4 "알림 꺼짐 — 시스템 설정에서 켜기").
///
/// 한 번 거부된 뒤에는 앱이 프롬프트를 다시 띄울 수 없다 — iOS 는 두 번째
/// 요청을 무시하고 Android 13+ 도 두 번 거부되면 그렇다. 그래서 사용자가
/// 켤 수 있는 **유일한 자리**로 보낸다.
///
/// `url_launcher` 로는 안 된다: iOS 는 `app-settings:` 스킴이 열리지만 Android
/// 는 설정 화면이 URL 이 아니라 인텐트(`ACTION_APP_NOTIFICATION_SETTINGS`)다.
/// 테스트는 이 provider 를 가짜로 덮는다(`webLinkLauncherProvider` 와 같은 모양).
final openNotificationSettingsProvider = Provider<Future<void> Function()>(
  (ref) =>
      () => AppSettings.openAppSettings(type: AppSettingsType.notification),
);
