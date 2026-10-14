import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/ad_banner_slot.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('reservedHeightFor', () {
    test('폰 폭은 50, 728 부터는 90 (경계 727/728)', () {
      expect(AdBannerSlot.reservedHeightFor(390), 50);
      expect(AdBannerSlot.reservedHeightFor(727), 50);
      expect(AdBannerSlot.reservedHeightFor(728), 90);
      expect(AdBannerSlot.reservedHeightFor(1366), 90);
    });
  });

  // 태블릿 폭 슬롯을 재려면 테스트 표면(기본 800×600)부터 넓혀야 한다.
  Future<void> pumpSlot(
    WidgetTester tester,
    double width, {
    Widget Function(BuildContext, double)? builder,
  }) async {
    tester.view.physicalSize = Size(width + 100, 400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(Brightness.light),
        home: Align(
          alignment: Alignment.topLeft,
          child: SizedBox(
            width: width,
            child: AdBannerSlot(builder: builder),
          ),
        ),
      ),
    );
  }

  testWidgets('좁은 슬롯은 50 + 여백 8 을 예약한다', (tester) async {
    await pumpSlot(tester, 390);

    expect(
      tester.getSize(find.byType(AdBannerSlot)).height,
      50 + AdBannerSlot.contentGap,
    );
  });

  testWidgets('태블릿 콘텐츠 열 폭에서는 90 + 여백 8 을 예약한다', (tester) async {
    await pumpSlot(tester, 940);

    expect(
      tester.getSize(find.byType(AdBannerSlot)).height,
      90 + AdBannerSlot.contentGap,
    );
  });

  // 티켓 31 은 이 폭으로 어댑티브 배너를 로드한다.
  testWidgets('현재 슬롯 폭을 bannerWidth 로 넘겨준다', (tester) async {
    final widths = <double>[];

    await pumpSlot(
      tester,
      940,
      builder: (context, bannerWidth) {
        widths.add(bannerWidth);
        return const SizedBox();
      },
    );

    expect(widths, [940]);
  });
}
