import 'package:chosung/l10n/app_localization.dart';
import 'package:chosung/notifications/notification_controller.dart';
import 'package:chosung/routing/app_router.dart';
import 'package:chosung/subscription/entitlement_refresh.dart';
import 'package:chosung/subscription/purchase_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class ChosungApp extends ConsumerWidget {
  const ChosungApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // 로컬 알림 동기화는 화면이 아니라 앱 수명에 매달려 있어야 한다(티켓 30) —
    // 설정 탭을 한 번도 안 열어도 돌아야 하고, 탭을 옮겨도 끊기면 안 된다.
    // `watch` 가 아니라 `listen` 인 이유는 계획이 바뀔 때마다 앱 전체를 다시
    // 그릴 이유가 없기 때문이다(구독은 provider 를 살려 두기만 한다).
    //
    // 구매 흐름도 같은 이유로 앱 수명에 매달린다(티켓 32) — 지난 실행에서
    // 끊긴 구매는 **첫 프레임 직후** 구매 스트림으로 올라오므로, Paywall 을
    // 열 때 비로소 듣기 시작하면 그 거래를 놓친다(Play 는 3일 내 acknowledge
    // 가 없으면 자동 환불한다).
    //
    // 구독 권한 재확인도 같은 이유로 앱 수명에 매달린다(티켓 33) — 포그라운드에
    // 머무는 동안 `next_check_at` 에 맞춰 `/me/stats` 를 다시 불러야 하고, 그
    // 타이머가 탭을 옮길 때 끊기면 환불 반영이 세션 내내 안 온다.
    ref
      ..listen(notificationSyncProvider, (_, _) {})
      ..listen(purchaseFlowProvider, (_, _) {})
      ..listen(entitlementRefreshProvider, (_, _) {});

    return MaterialApp.router(
      routerConfig: ref.watch(appRouterProvider),
      debugShowCheckedModeBanner: false,
      theme: appTheme(Brightness.light),
      darkTheme: appTheme(Brightness.dark),
      // 다크모드는 시스템 추종, 수동 토글 없음(OVERRIDES §9) — MaterialApp 의
      // 기본값(ThemeMode.system)이 그 규칙이라 따로 넘기지 않는다.
      locale: context.locale,
      supportedLocales: context.supportedLocales,
      localizationsDelegates: context.localizationDelegates,
      onGenerateTitle: (context) => 'app.name'.tr(),
    );
  }
}

/// UI 언어는 기기 설정을 따른다 — `saveLocale: false` 라서 선택한 언어를
/// 저장하지는 않지만, 기기 언어를 읽어오는 건 `initializeLocalization()`
/// (`EasyLocalization.ensureInitialized()`) 뿐이라 **그 호출이 반드시 먼저**
/// 있어야 한다. 퍼즐 언어는 서버에 저장되는 별도 선호값이다.
class AppLocalizationScope extends StatelessWidget {
  const AppLocalizationScope({
    required this.child,
    this.startLocale,
    super.key,
  });

  final Widget child;

  /// 테스트에서 기기 언어를 고정한다. 앱에서는 null — 기기 설정을 따른다.
  final Locale? startLocale;

  @override
  Widget build(BuildContext context) => EasyLocalization(
    supportedLocales: AppLocalization.supportedLocales,
    fallbackLocale: AppLocalization.fallbackLocale,
    startLocale: startLocale,
    path: AppLocalization.path,
    saveLocale: false,
    child: child,
  );
}
