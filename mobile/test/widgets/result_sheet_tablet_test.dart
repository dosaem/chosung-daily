import 'package:chosung/layout/adaptive_sheet.dart';
import 'package:chosung/puzzle/share_text.dart';
import 'package:chosung/widgets/result_sheet.dart';
import 'package:chosung/widgets/stat_bar.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'result_sheet_test.dart' show openResultSheet, tapAndSettle;

/// SCREENS T2: compact 는 바텀시트, medium 이상은 가운데 다이얼로그(최대 560).
/// 내용 위젯은 하나라 같은 테스트를 두 폭에서 돌린다.
void main() {
  // 폰 폭(390)은 `openResultSheet` 의 기본값이다.
  testWidgets('폰 폭(390)은 바텀시트로 뜨고 손잡이가 있다', (tester) async {
    await openResultSheet(tester);

    expect(find.byType(BottomSheet), findsOne);
    expect(find.byType(Dialog), findsNothing);
    expect(find.byType(StatBar), findsOne);
  });

  testWidgets('태블릿 폭(744)은 가운데 다이얼로그 — 최대 560, 상하 여백 48 이상', (tester) async {
    await openResultSheet(tester, size: const Size(744, 1024));

    expect(find.byType(Dialog), findsOne);
    expect(find.byType(BottomSheet), findsNothing);

    final sheet = tester.getRect(find.byType(ResultSheet));
    expect(sheet.width, lessThanOrEqualTo(AdaptiveSheet.maxDialogWidth));
    expect(sheet.center.dx, 372);
    expect(sheet.top, greaterThanOrEqualTo(AdaptiveSheet.dialogVerticalInset));
    expect(
      sheet.bottom,
      lessThanOrEqualTo(1024 - AdaptiveSheet.dialogVerticalInset),
    );
  });

  testWidgets('744 에서도 분포·카운트다운·버튼이 다 있다', (tester) async {
    await openResultSheet(tester, size: const Size(744, 1024));

    expect(find.text('정답은 지하철역!'), findsOne);
    expect(find.byType(StatBar), findsOne);
    expect(
      find.textContaining(RegExp(r'^다음 퍼즐까지 \d\d:\d\d:\d\d$')),
      findsOne,
    );
    expect(find.text('결과 공유'), findsOne);
    expect(find.text('순위 보기'), findsOne);
  });

  testWidgets('744 에서 공유·순위 버튼 동작이 폰과 같다', (tester) async {
    final opened = await openResultSheet(tester, size: const Size(744, 1024));

    await tapAndSettle(tester, find.text('결과 공유'));

    expect(opened.shared.single, contains('2/5 성공'));
    expect(opened.shared.single, contains(shareUrl));
    expect(opened.analytics.logged.map((event) => event.name), ['share']);

    await tapAndSettle(tester, find.text('순위 보기'));

    expect(opened.rankingTaps, ['ranking']);
    expect(find.byType(ResultSheet), findsNothing);
  });

  // 끌어내릴 방향이 없는 다이얼로그엔 손잡이를 두지 않는다.
  testWidgets('손잡이는 바텀시트에만 있다', (tester) async {
    await openResultSheet(tester);
    final phoneHandles = _handleCount(tester);

    await openResultSheet(tester, size: const Size(744, 1024));
    final tabletHandles = _handleCount(tester);

    expect(phoneHandles, 1);
    expect(tabletHandles, 0);
  });

  testWidgets('expanded 폭(1024)도 같은 다이얼로그다', (tester) async {
    await openResultSheet(tester, size: const Size(1024, 768));

    expect(find.byType(Dialog), findsOne);
    expect(
      tester.getRect(find.byType(ResultSheet)).width,
      lessThanOrEqualTo(AdaptiveSheet.maxDialogWidth),
    );
  });
}

/// 손잡이는 48×4 컨테이너 하나다(`_SheetHandle`).
int _handleCount(WidgetTester tester) => find
    .descendant(
      of: find.byType(ResultSheet),
      matching: find.byWidgetPredicate(
        (widget) =>
            widget is Container &&
            widget.constraints?.maxWidth == 48 &&
            widget.constraints?.maxHeight == 4,
      ),
    )
    .evaluate()
    .length;
