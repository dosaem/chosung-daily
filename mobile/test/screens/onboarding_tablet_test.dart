import 'package:chosung/api/api_models.dart';
import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/screens/onboarding_screen.dart';
import 'package:chosung/widgets/puzzle_board.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'onboarding_screen_test.dart' show OnboardingHarness;

/// SCREENS T0: 온보딩은 rail 없이 `ReadingWidth` 600 가운데다. 폰과 다른 건
/// 양옆 여백뿐이고 타일·삽화 크기는 그대로다.
const _tabletLandscape = Size(1024, 768);

Future<void> _swipeToNextPage(WidgetTester tester) async {
  await tester.drag(find.byKey(OnboardingKeys.pages), const Offset(-400, 0));
  await tester.pumpAndSettle();
}

Future<void> _tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.runAsync(() async {
    await tester.tap(finder);
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

double _bodyWidth(WidgetTester tester) => tester
    .getSize(
      find
          .descendant(
            of: find.byType(ReadingWidth),
            matching: find.byType(ConstrainedBox),
          )
          .first,
    )
    .width;

void main() {
  testWidgets('폭 1024 가로에서도 본문은 읽기 폭 600 가운데다', (tester) async {
    await OnboardingHarness().pump(tester, size: _tabletLandscape);

    expect(find.byType(OnboardingScreen), findsOne);
    // 온보딩은 셸 밖이라 rail 이 없다(SCREENS T0).
    expect(find.byType(NavigationRail), findsNothing);
    expect(_bodyWidth(tester), ReadingWidth.defaultMaxWidth);
  });

  testWidgets('타일 크기는 폰과 같다 — 폭이 넓다고 키우지 않는다', (tester) async {
    await OnboardingHarness().pump(tester);
    final phone = tester.getSize(find.byType(BoardTile).first);

    await OnboardingHarness().pump(tester, size: _tabletLandscape);

    expect(tester.getSize(find.byType(BoardTile).first), phone);
  });

  testWidgets('폭 1024 가로에서 3장을 스와이프로 넘긴다', (tester) async {
    await OnboardingHarness(isIos: false).pump(tester, size: _tabletLandscape);

    expect(find.text('하루 한 문제'), findsOne);

    await _swipeToNextPage(tester);
    expect(find.text('5번의 기회'), findsOne);

    await _swipeToNextPage(tester);
    expect(find.text('매일 이어가기'), findsOne);
    // 알림 사전 안내 카드도 같은 읽기 폭 안에 있다.
    expect(find.text('매일 아침 알려드릴까요?'), findsOne);
    expect(_bodyWidth(tester), ReadingWidth.defaultMaxWidth);

    // 마지막 장이라 더 넘어가지 않는다(Android 는 ATT 안내가 없다).
    await _swipeToNextPage(tester);
    expect(find.text('매일 이어가기'), findsOne);
  });

  testWidgets('폭 1024 가로에서 언어 칩이 동작한다', (tester) async {
    final harness = OnboardingHarness();
    await harness.pump(tester, size: _tabletLandscape);

    await _tapAndSettle(
      tester,
      find.byKey(OnboardingKeys.languageChip(PuzzleLanguage.en)),
    );

    expect(harness.api.updatedPuzzleLanguages, [PuzzleLanguage.en]);
    expect(find.text('L'), findsOne);
  });

  testWidgets('ATT 안내 카드도 읽기 폭 안에 선다(iOS 태블릿)', (tester) async {
    await OnboardingHarness().pump(tester, size: _tabletLandscape);

    await _tapAndSettle(tester, find.text('다음'));
    await _tapAndSettle(tester, find.text('다음'));
    await _tapAndSettle(tester, find.text('나중에'));

    expect(find.text('맞춤 광고 허용'), findsOne);
    expect(_bodyWidth(tester), ReadingWidth.defaultMaxWidth);
  });
}
