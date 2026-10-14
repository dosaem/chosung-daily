import 'package:chosung/layout/adaptive_sheet.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// 26(결과 시트)·29(백업 코드·삭제)·32(Paywall) 가 같은 내용 위젯을 이 함수에
/// 넘긴다 — 폭에 따라 시트/다이얼로그가 갈려도 내용은 하나다.
const _content = SizedBox(
  key: ValueKey('sheet-body'),
  height: 200,
  child: Text('정답은 지하철역!'),
);

/// 화면 폭을 바꾼다.
///
/// `tester.binding.setSurfaceSize` 는 Flutter 3.38 에서 `MediaQuery` 에 반영되지
/// 않는다(표면만 바뀌고 `MediaQuery.sizeOf(context).width` 는 기본 800 그대로다 —
/// 직접 확인). 그래서 뷰의 물리 크기를 고친다. 회전·Split View 가 실제로
/// 바꾸는 값도 이쪽이다.
void setViewSize(WidgetTester tester, Size size) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
}

Future<String?> _open(WidgetTester tester, Size size) async {
  setViewSize(tester, size);

  String? result;
  await tester.pumpWidget(
    MaterialApp(
      theme: appTheme(Brightness.light),
      home: Builder(
        builder: (context) => Scaffold(
          body: TextButton(
            onPressed: () async {
              result = await showAdaptiveSheet<String>(
                context: context,
                builder: (context) => _content,
              );
            },
            child: const Text('열기'),
          ),
        ),
      ),
    ),
  );

  await tester.tap(find.text('열기'));
  await tester.pumpAndSettle();
  return result;
}

void main() {
  testWidgets('폰 폭은 바텀시트로 뜬다', (tester) async {
    await _open(tester, const Size(390, 844));

    expect(find.byType(BottomSheet), findsOne);
    expect(find.byType(Dialog), findsNothing);
    expect(find.text('정답은 지하철역!'), findsOne);
    // 바텀시트는 화면 아래에 붙는다.
    expect(
      tester.getRect(find.byKey(const ValueKey('sheet-body'))).bottom,
      844,
    );
  });

  testWidgets('태블릿 폭은 가운데 다이얼로그 — 최대 폭 560, 상하 여백 48 이상', (tester) async {
    await _open(tester, const Size(1024, 768));

    expect(find.byType(Dialog), findsOne);
    expect(find.byType(BottomSheet), findsNothing);

    final body = tester.getRect(find.byKey(const ValueKey('sheet-body')));
    expect(body.width, lessThanOrEqualTo(AdaptiveSheet.maxDialogWidth));
    expect(body.top, greaterThanOrEqualTo(AdaptiveSheet.dialogVerticalInset));
    expect(
      body.bottom,
      lessThanOrEqualTo(768 - AdaptiveSheet.dialogVerticalInset),
    );
    // 가운데 정렬.
    expect(body.center.dx, 512);
  });

  testWidgets('medium 경계(600)부터 다이얼로그다', (tester) async {
    await _open(tester, const Size(600, 900));

    expect(find.byType(Dialog), findsOne);
  });

  testWidgets('어느 쪽이든 닫을 때 같은 값을 돌려준다', (tester) async {
    setViewSize(tester, const Size(1024, 768));

    String? result;
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(Brightness.light),
        home: Builder(
          builder: (context) => Scaffold(
            body: TextButton(
              onPressed: () async {
                result = await showAdaptiveSheet<String>(
                  context: context,
                  builder: (context) => TextButton(
                    onPressed: () => Navigator.of(context).pop('공유'),
                    child: const Text('결과 공유'),
                  ),
                );
              },
              child: const Text('열기'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('열기'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('결과 공유'));
    await tester.pumpAndSettle();

    expect(result, '공유');
  });
}
