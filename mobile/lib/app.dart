import 'package:chosung/l10n/app_localization.dart';
import 'package:chosung/routing/app_router.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class ChosungApp extends ConsumerWidget {
  const ChosungApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => MaterialApp.router(
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

/// UI 언어는 기기 설정을 따른다 — `saveLocale: false` 라서 저장소(shared_preferences)를
/// 건드리지 않고, 그래서 `EasyLocalization.ensureInitialized()` 도 필요 없다.
/// 퍼즐 언어는 서버에 저장되는 별도 선호값이다.
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
