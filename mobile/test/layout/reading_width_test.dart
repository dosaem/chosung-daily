import 'package:chosung/layout/reading_width.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  Future<Size> pumpIn(WidgetTester tester, double width, Widget child) async {
    await tester.pumpWidget(
      Directionality(
        textDirection: TextDirection.ltr,
        child: Center(
          child: SizedBox(width: width, height: 400, child: child),
        ),
      ),
    );
    return tester.getSize(find.byKey(const ValueKey('body')));
  }

  // 읽기 폭이 준 만큼 채우는 본문 — 폭을 그대로 재려면 늘어나는 위젯이어야 한다.
  const body = SizedBox.expand(key: ValueKey('body'));

  testWidgets('태블릿 폭에서 본문을 기본 600 으로 가둔다', (tester) async {
    final size = await pumpIn(
      tester,
      1024,
      const ReadingWidth(child: body),
    );

    expect(size.width, ReadingWidth.defaultMaxWidth);
  });

  testWidgets('화면별로 더 좁은 읽기 폭을 줄 수 있다 (T4 의 480 열)', (tester) async {
    final size = await pumpIn(
      tester,
      1024,
      const ReadingWidth(maxWidth: 480, child: body),
    );

    expect(size.width, 480);
  });

  testWidgets('폰 폭에서는 화면을 그대로 채운다', (tester) async {
    final size = await pumpIn(tester, 390, const ReadingWidth(child: body));

    expect(size.width, 390);
  });
}
