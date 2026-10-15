import 'package:chosung/onboarding/onboarding_pages.dart';
import 'package:chosung/screens/onboarding_screen.dart';
import 'package:chosung/widgets/leaderboard_row.dart';
import 'package:chosung/widgets/result_sheet.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../integration_test/store_screenshot_scenes.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 스토어 스크린샷 장면(티켓 35)을 시뮬레이터 없이 검사한다.
///
/// `flutter drive` 는 시뮬레이터가 있어야 돌아서 CI 가 못 돈다. 그래서 **같은
/// 장면 정의**를 위젯 테스트가 폰·태블릿 폭으로 띄워, 스크린샷을 찍으러 가기
/// 전에 "장면이 비었다 / 태블릿인데 폰 레이아웃이다" 를 여기서 잡는다.
///
/// 태블릿 조건은 티켓의 불합격 기준 그대로다 — 폭 ≥600 에서 `NavigationRail` 이
/// 없으면 폰 레이아웃을 가운데 띄운 결과라 스크린샷으로 쓸 수 없다.
void main() {
  const phone = Size(430, 932); // iPhone 6.9"
  const tablet = Size(1024, 1366); // iPad 13" 세로

  for (final locale in [const Locale('ko'), const Locale('en')]) {
    final language = locale.languageCode;

    for (final size in [phone, tablet]) {
      final label = size == phone ? '폰' : '태블릿';

      testWidgets('$language · $label — 5장이 모두 그려진다', (tester) async {
        setViewSize(tester, size);

        final scenes = await _pumpAndCollect(
          tester,
          locale: locale,
          size: size,
        );

        expect(
          scenes.map((scene) => scene.scene).toSet(),
          StoreScene.values.toSet(),
          reason: 'OVERRIDES §8 의 5장 — 구독(S5)은 빼고 언어 선택(S6)을 넣는다',
        );
      });

      testWidgets('$language · $label — 장면마다 그 화면의 내용이 보인다', (tester) async {
        setViewSize(tester, size);

        final scenes = storeScreenshotScenes(locale: locale, isIos: true);
        for (final scene in scenes) {
          await _pumpScene(tester, scene);

          switch (scene.scene) {
            case StoreScene.home:
              // 보드와 입력이 있고, 끝나지 않은 퍼즐이라 "결과 보기" 는 없다.
              expect(find.text('today.submit'.tr()), findsOneWidget);
              expect(find.text('today.show_result'.tr()), findsNothing);
            case StoreScene.result:
              // 시트가 떠 있다 — 폭에 따라 바텀시트/다이얼로그로 갈린다(T2).
              expect(find.byType(ResultSheet), findsOneWidget);
            case StoreScene.leaderboard:
              // 상위 5줄 + 목록 밖에 고정된 내 줄(S3 의 규칙이 다 보이는 장면).
              expect(find.byType(LeaderboardRow), findsNWidgets(6));
              expect(find.text('ranking.my_rank'.tr()), findsOneWidget);
            case StoreScene.records:
              expect(find.text('records.recent_days'.tr()), findsOneWidget);
              expect(find.text('records.settings'.tr()), findsOneWidget);
            case StoreScene.language:
              // 퍼즐 언어 칩이 있는 온보딩 1장(SCREENS S6 "칩은 1장 상단에만").
              expect(find.text('language.ko'.tr()), findsOneWidget);
              expect(find.text('language.en'.tr()), findsOneWidget);
          }
        }
      });
    }

    testWidgets('$language — 태블릿 폭의 셸 장면은 rail 로 찍힌다', (tester) async {
      setViewSize(tester, tablet);

      for (final scene in storeScreenshotScenes(locale: locale, isIos: true)) {
        await _pumpScene(tester, scene);

        expect(
          find.byType(NavigationRail),
          scene.scene.hasShell ? findsOneWidget : findsNothing,
          reason:
              '${scene.fileName}: 폭 ${tablet.width} — '
              // 온보딩은 rail 없이 읽기 폭 가운데로만 선다(SCREENS T0).
              '${scene.scene.hasShell ? "셸 화면은 rail" : "온보딩은 rail 없음"}',
        );
        expect(
          find.byType(NavigationBar),
          findsNothing,
          reason: scene.fileName,
        );
      }
    });

    testWidgets('$language — 폰 폭의 셸 장면은 하단 탭 바로 찍힌다', (tester) async {
      setViewSize(tester, phone);

      for (final scene in storeScreenshotScenes(locale: locale, isIos: true)) {
        await _pumpScene(tester, scene);

        expect(
          find.byType(NavigationBar),
          scene.scene.hasShell ? findsOneWidget : findsNothing,
          reason: scene.fileName,
        );
        expect(
          find.byType(NavigationRail),
          findsNothing,
          reason: scene.fileName,
        );
      }
    });

    // 티켓 38 이후: 서버는 언어 중립 태그만 주고 접두사·복수형은 화면이 붙인다.
    // 스토어에 올라가는 그림이라 **다른 언어의 글자가 섞이면 바로 반송 사유**다 —
    // 스크린샷을 찍으러 가기 전에 여기서 잡는다(`review/impl-evidence-35.md`
    // "리뷰 전 보정").
    testWidgets('$language — 리더보드 장면의 글자는 UI 언어뿐이다', (tester) async {
      setViewSize(tester, phone);

      final scene = storeScreenshotScenes(
        locale: locale,
        isIos: true,
      ).firstWhere((scene) => scene.scene == StoreScene.leaderboard);
      await _pumpScene(tester, scene);

      final texts = tester
          .widgetList<Text>(find.byType(Text))
          .map((text) => text.data ?? '')
          .toList();

      // 1위 줄은 UI 언어의 접두사 + 서버 태그다.
      expect(
        texts,
        contains('ranking.guest'.tr(namedArgs: {'tag': 'a3f1'})),
        reason: '접두사는 UI 언어가 붙인다(README "38.")',
      );
      // 1회 시도 줄의 복수형. en 은 "1 try", ko 는 "1회".
      expect(
        texts,
        contains('ranking.attempts'.plural(1, name: 'count')),
        reason: 'en 은 1 회에 "1 tries" 가 아니라 "1 try" 여야 한다',
      );

      final foreign = language == 'ko' ? 'Guest' : '게스트';
      expect(
        texts.where((text) => text.contains(foreign)),
        isEmpty,
        reason: '$language 스크린샷에 "$foreign" 가 섞이면 안 된다',
      );
      if (language == 'en') {
        expect(
          texts.where((text) => text.contains('1 tries')),
          isEmpty,
          reason: '티켓 38 에서 고친 복수형이 되돌아가지 않았는지',
        );
      }
    });

    // 최종 리뷰 D-35-5: 장면이 플랫폼을 iOS 로 박아 둬서, Android 에뮬레이터에서
    // 찍어도 ATT 안내 1장이 붙은 iPhone 온보딩(4장)이 나왔다. Play 는 실제 앱
    // 경험을 보여 주도록 요구한다 — 찍는 기기의 구성이 그대로 나와야 한다.
    // 최종 리뷰 D-35-8: 폰 폭만 보던 이 단언을 **태블릿 폭까지** 돌린다.
    // `onboardingPages` 는 화면 폭을 보지 않고 플랫폼 하나로만 갈리므로, Play
    // 태블릿 세트를 iPad(iOS) 캡처로 채우면 폰과 똑같이 ATT 안내 장이 올라간다.
    for (final isIos in [true, false]) {
      final platform = isIos ? 'iOS' : 'Android';

      for (final size in [phone, tablet]) {
        final width = size == phone ? '폰' : '태블릿';

        testWidgets('$language · $platform · $width — 온보딩 장 수가 그 플랫폼과 같다', (
          tester,
        ) async {
          setViewSize(tester, size);

          final scene = storeScreenshotScenes(
            locale: locale,
            isIos: isIos,
          ).firstWhere((scene) => scene.scene == StoreScene.language);
          await _pumpScene(tester, scene);

          final pages = onboardingPages(isIos: isIos);
          for (var index = 0; index < pages.length; index++) {
            expect(
              find.byKey(OnboardingKeys.dot(index)),
              findsOneWidget,
              reason: '$platform·$width 은 ${pages.length}장이다',
            );
          }
          expect(
            find.byKey(OnboardingKeys.dot(pages.length)),
            findsNothing,
            reason: '$platform·$width 에 없는 장이 그려졌다 — ${pages.length}장이어야 한다',
          );
        });
      }
    }

    testWidgets('$language — 모든 장면이 라이트 모드다(기기가 다크여도)', (tester) async {
      setViewSize(tester, phone);
      tester.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
      addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);

      for (final scene in storeScreenshotScenes(locale: locale, isIos: true)) {
        await _pumpScene(tester, scene);

        final context = tester.element(find.byType(Scaffold).first);
        expect(
          Theme.of(context).brightness,
          Brightness.light,
          reason: '${scene.fileName} — OVERRIDES §8 은 라이트 모드 기준이다',
        );
      }
    });
  }
}

/// 장면을 띄우고 `revealLabel` 이 있으면 눌러서 완성한다. 번역 JSON 과 가짜
/// 응답은 실제 이벤트 루프에서 끝나므로 첫 프레임은 `runAsync` 안에서 돌린다
/// (다른 화면 테스트와 같은 방식).
Future<void> _pumpScene(WidgetTester tester, StoreScreenshotScene scene) async {
  await tester.runAsync(() async {
    await tester.pumpWidget(scene.app);
    await tester.pump();
  });
  await tester.pumpAndSettle();

  final key = scene.revealLabelKey;
  if (key == null) return;

  await tester.runAsync(() async {
    // 번역은 앱이 뜬 뒤에 푼다 — 장면을 만들 때 풀면 키가 그대로 남는다.
    await tester.tap(find.text(key.tr()));
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

/// 5장을 차례로 띄워 보고 그 목록을 돌려준다.
Future<List<StoreScreenshotScene>> _pumpAndCollect(
  WidgetTester tester, {
  required Locale locale,
  required Size size,
}) async {
  final scenes = <StoreScreenshotScene>[];
  for (final scene in storeScreenshotScenes(locale: locale, isIos: true)) {
    await _pumpScene(tester, scene);
    expect(find.byType(MaterialApp), findsOneWidget, reason: scene.fileName);
    scenes.add(scene);
  }
  return scenes;
}
