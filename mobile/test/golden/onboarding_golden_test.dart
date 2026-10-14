import 'dart:io';

import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/screens/onboarding_screen.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 목업 `design/stitch/e6_onboarding.html`(1장)과 눈으로 대조할 스크린샷.
/// 2·3장과 ATT/알림 안내는 목업이 없어서(스펙 "디자인 부족 항목") 여기 골든이
/// 그 자리를 대신한다 — 명세 + OVERRIDES 토큰으로 만든 결과를 남겨 둔다.
///
/// 갱신: `flutter test test/golden --update-goldens`
Future<void> _loadFonts() async {
  final pretendard = FontLoader('Pretendard');
  for (final path in [
    'assets/fonts/Pretendard-Regular.otf',
    'assets/fonts/Pretendard-SemiBold.otf',
    'assets/fonts/Pretendard-Bold.otf',
  ]) {
    pretendard.addFont(
      File(path).readAsBytes().then((bytes) => ByteData.view(bytes.buffer)),
    );
  }
  await pretendard.load();

  final lucide = FontLoader('packages/lucide_icons/Lucide')
    ..addFont(rootBundle.load('packages/lucide_icons/assets/lucide.ttf'));
  await lucide.load();
}

Widget _onboarding(Brightness brightness) => ProviderScope(
  retry: noAutoRetry,
  overrides: [
    apiClientProvider.overrideWithValue(FakeApiClient()),
    startupStatsProvider.overrideWithValue(fakeMyStats()),
    isIosProvider.overrideWithValue(true),
  ],
  child: AppLocalizationScope(
    startLocale: const Locale('ko'),
    child: Builder(
      builder: (context) => MaterialApp(
        theme: appTheme(brightness),
        debugShowCheckedModeBanner: false,
        locale: context.locale,
        supportedLocales: context.supportedLocales,
        localizationsDelegates: context.localizationDelegates,
        home: const OnboardingScreen(),
      ),
    ),
  ),
);

void main() {
  setUpAll(_loadFonts);

  for (final shot in [
    (
      name: 'onboarding_light_390',
      size: const Size(390, 844),
      brightness: Brightness.light,
      page: 0,
    ),
    (
      name: 'onboarding_dark_390',
      size: const Size(390, 844),
      brightness: Brightness.dark,
      page: 0,
    ),
    // 알림 사전 안내(3장) — 목업 없음.
    (
      name: 'onboarding_notice_390',
      size: const Size(390, 844),
      brightness: Brightness.light,
      page: 2,
    ),
    // ATT 사전 안내(4장, iOS 만) — 목업 없음.
    (
      name: 'onboarding_tracking_390',
      size: const Size(390, 844),
      brightness: Brightness.light,
      page: 3,
    ),
    (
      name: 'onboarding_tablet_1024',
      size: const Size(1024, 768),
      brightness: Brightness.light,
      page: 0,
    ),
  ]) {
    testWidgets('골든: ${shot.name}', (tester) async {
      setViewSize(tester, shot.size);
      await tester.runAsync(() async {
        await tester.pumpWidget(_onboarding(shot.brightness));
        await tester.pump();
      });
      await tester.pumpAndSettle();

      for (var step = 0; step < shot.page; step++) {
        // 3장(알림 사전 안내)의 주 버튼은 "다음" 이 아니라 권한 요청이다 —
        // 골든은 프롬프트를 띄우지 않고 "나중에" 로 넘어간다.
        await tester.tap(find.text(step == 2 ? '나중에' : '다음'));
        await tester.pumpAndSettle();
      }

      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('${shot.name}.png'),
      );
    });
  }
}
