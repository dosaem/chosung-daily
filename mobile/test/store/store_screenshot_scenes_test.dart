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

        for (final scene in storeScreenshotScenes(locale: locale)) {
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

      for (final scene in storeScreenshotScenes(locale: locale)) {
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

      for (final scene in storeScreenshotScenes(locale: locale)) {
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

    testWidgets('$language — 모든 장면이 라이트 모드다(기기가 다크여도)', (tester) async {
      setViewSize(tester, phone);
      tester.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
      addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);

      for (final scene in storeScreenshotScenes(locale: locale)) {
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
  for (final scene in storeScreenshotScenes(locale: locale)) {
    await _pumpScene(tester, scene);
    expect(find.byType(MaterialApp), findsOneWidget, reason: scene.fileName);
    scenes.add(scene);
  }
  return scenes;
}
