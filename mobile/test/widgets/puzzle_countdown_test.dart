import 'package:chosung/widgets/puzzle_countdown.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// 가짜 시계로 본다 — `DateTime.now()` 는 테스트에서도 실제 시각이라
/// `tester.pump(1초)` 로는 남은 시간이 1초 줄지 않는다.
Widget _countdown(DateTime Function() now) => MaterialApp(
  home: PuzzleCountdown(
    now: now,
    builder: (context, remaining) => Text(remaining),
  ),
);

void main() {
  // KST 23:47:27 = UTC 14:47:27. 다음 KST 자정까지 12분 33초.
  testWidgets('기기 시간대와 무관하게 KST 자정까지를 센다', (tester) async {
    await tester.pumpWidget(
      _countdown(() => DateTime.utc(2026, 10, 13, 14, 47, 27)),
    );

    expect(find.text('00:12:33'), findsOne);
  });

  testWidgets('1초마다 다시 그린다', (tester) async {
    var now = DateTime.utc(2026, 10, 13, 14, 47, 27);

    await tester.pumpWidget(_countdown(() => now));
    expect(find.text('00:12:33'), findsOne);

    now = now.add(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));

    expect(find.text('00:12:32'), findsOne);
  });

  testWidgets('위젯이 사라지면 타이머도 멈춘다', (tester) async {
    await tester.pumpWidget(
      _countdown(() => DateTime.utc(2026, 10, 13, 14, 47, 27)),
    );

    // 남은 타이머가 있으면 테스트 프레임워크가 여기서 실패한다.
    await tester.pumpWidget(const MaterialApp(home: SizedBox()));
    await tester.pump(const Duration(seconds: 2));

    expect(find.text('00:12:33'), findsNothing);
  });
}
