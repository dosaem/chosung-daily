import 'package:chosung/layout/app_breakpoint.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AppBreakpoint.fromWidth 경계', () {
    test('599 는 compact, 600 은 medium', () {
      expect(AppBreakpoint.fromWidth(599), AppBreakpoint.compact);
      expect(AppBreakpoint.fromWidth(600), AppBreakpoint.medium);
    });

    test('839 는 medium, 840 은 expanded', () {
      expect(AppBreakpoint.fromWidth(839), AppBreakpoint.medium);
      expect(AppBreakpoint.fromWidth(840), AppBreakpoint.expanded);
    });

    test('iPad Split View 의 가장 좁은 폭(약 320)은 compact 로 떨어진다', () {
      expect(AppBreakpoint.fromWidth(320), AppBreakpoint.compact);
    });

    test('rail 은 medium 이상에서만 쓴다', () {
      expect(AppBreakpoint.compact.hasRail, isFalse);
      expect(AppBreakpoint.medium.hasRail, isTrue);
      expect(AppBreakpoint.expanded.hasRail, isTrue);
    });
  });

  // 기기 종류·OS 가 아니라 "지금 이 순간의 폭" 으로만 판정해야 회전과 iPad
  // Split View 에서 같은 기기가 구간을 넘나들 수 있다.
  testWidgets('MediaQuery 의 현재 폭만 본다 — 높이·플랫폼은 보지 않는다', (tester) async {
    final seen = <AppBreakpoint>[];

    Future<void> pumpWidth(double width) async {
      await tester.pumpWidget(
        MediaQuery(
          data: MediaQueryData(size: Size(width, 1400)),
          child: Builder(
            builder: (context) {
              seen.add(AppBreakpoint.of(context));
              return const SizedBox();
            },
          ),
        ),
      );
    }

    // 같은 iPad 가 세로 전체 → Split View 1/2 → 1/3 로 줄어드는 흐름.
    await pumpWidth(1024);
    await pumpWidth(744);
    await pumpWidth(320);

    expect(seen, [
      AppBreakpoint.expanded,
      AppBreakpoint.medium,
      AppBreakpoint.compact,
    ]);
  });
}
