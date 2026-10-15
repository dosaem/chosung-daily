import 'dart:io';

import 'package:chosung/layout/app_breakpoint.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'store_screenshot_scenes.dart';

/// 스토어 스크린샷을 시뮬레이터에서 찍는다(티켓 35). 장면 정의는
/// `store_screenshot_scenes.dart` 에 있고 CI 는 그걸 위젯 테스트로 검사한다.
///
///     STORE_SHOT_DIR=<출력경로> flutter drive \
///       --driver=test_driver/integration_test.dart \
///       --target=integration_test/store_screenshots_test.dart \
///       -d <기기 UDID> --dart-define=SHOT_LOCALE=ko
///
/// 보통은 `scripts/store_screenshots.sh` 가 기기 목록·상태바·폴더까지 맞춰
/// 이 명령을 돌린다.
const _locale = String.fromEnvironment('SHOT_LOCALE', defaultValue: 'ko');

/// 어느 플랫폼 구성으로 찍을지. 비우면 **이 기기**를 따른다(보통 그게 맞다).
/// `false` 를 넘기는 자리는 하나다: Android 에뮬레이터가 없을 때 Play 폰 세트를
/// iPhone 시뮬레이터에서 찍는 경우 — 그때도 그림은 Android 구성이어야 한다
/// (Play 는 실제 앱 경험을 요구한다. 최종 리뷰 D-35-5).
const _isIosOverride = String.fromEnvironment('SHOT_IS_IOS');

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('스토어 스크린샷 5장 ($_locale)', (tester) async {
    // 번역 JSON 은 앱과 같은 경로로 읽는다 — 안 부르면 첫 프레임에서 죽는다.
    await EasyLocalization.ensureInitialized();

    if (Platform.isAndroid) {
      // Android 는 Flutter surface 를 이미지로 바꿔야 스크린샷이 나온다.
      await binding.convertFlutterSurfaceToImage();
    }

    final size = tester.view.physicalSize / tester.view.devicePixelRatio;
    final breakpoint = AppBreakpoint.fromWidth(size.width);
    debugPrint(
      'store screenshots: $_locale, ${size.width}x${size.height}, $breakpoint',
    );

    // 장면은 **이 기기의** 플랫폼으로 만든다 — iOS 를 박아 두면 Android
    // 에뮬레이터에서 찍어도 iPhone 온보딩(ATT 1장 추가)이 나온다(D-35-5).
    final isIos = _isIosOverride.isEmpty
        ? Platform.isIOS
        : _isIosOverride == 'true';
    final scenes = storeScreenshotScenes(
      locale: const Locale(_locale),
      isIos: isIos,
    );
    debugPrint(
      'store screenshots: isIos=$isIos (기기 ${Platform.operatingSystem})',
    );

    for (final scene in scenes) {
      await tester.pumpWidget(scene.app);
      // 폰트·가짜 응답이 실제 시간으로 끝난다 — 고정 대기 + settle 로 맞춘다.
      await Future<void>.delayed(const Duration(seconds: 2));
      await tester.pumpAndSettle();

      final revealKey = scene.revealLabelKey;
      if (revealKey != null) {
        await tester.tap(find.text(revealKey.tr()));
        await tester.pumpAndSettle();
        await Future<void>.delayed(const Duration(milliseconds: 500));
        await tester.pumpAndSettle();
      }

      // 티켓 35 의 불합격 기준: 태블릿 폭에서 폰 레이아웃을 가운데 띄운 결과는
      // 쓸 수 없다. 찍기 **전에** rail 을 단언해서 그 그림이 파일로 남지 않게 한다.
      if (breakpoint.hasRail && scene.scene.hasShell) {
        expect(
          find.byType(NavigationRail),
          findsOneWidget,
          reason:
              '${scene.fileName}: 폭 ${size.width} 는 rail 구간인데 rail 이 없다 '
              '— 폰 레이아웃이 찍히려던 중이다(SCREENS T0)',
        );
        expect(
          find.byType(NavigationBar),
          findsNothing,
          reason: scene.fileName,
        );
      }

      await binding.takeScreenshot(scene.fileName);
    }
  });
}
