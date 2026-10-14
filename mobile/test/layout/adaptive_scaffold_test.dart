import 'package:chosung/layout/adaptive_scaffold.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/ad_banner_slot.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// 실제 셸과 같은 모양의 껍데기 — 탭 3개, 배너 슬롯, 본문에 입력창과 목록.
/// 본문 안의 상태(입력 중 텍스트·스크롤 위치)가 폭 변화를 넘기는지 보려면
/// 외부 컨트롤러 없이 위젯 자기 State 에 상태가 있어야 한다.
class _ShellHarness extends StatefulWidget {
  const _ShellHarness();

  @override
  State<_ShellHarness> createState() => _ShellHarnessState();
}

class _ShellHarnessState extends State<_ShellHarness> {
  int selectedIndex = 0;

  @override
  Widget build(BuildContext context) => MaterialApp(
    theme: appTheme(Brightness.light),
    home: AdaptiveScaffold(
      selectedIndex: selectedIndex,
      onDestinationSelected: (index) => setState(() => selectedIndex = index),
      destinations: const [
        AdaptiveDestination(icon: LucideIcons.grid, label: '오늘'),
        AdaptiveDestination(icon: LucideIcons.trophy, label: '순위'),
        AdaptiveDestination(icon: LucideIcons.calendar, label: '내 기록'),
      ],
      banner: const AdBannerSlot(),
      body: Column(
        children: [
          Text('탭 $selectedIndex'),
          const TextField(),
          Expanded(
            child: ListView(
              children: [
                for (var i = 0; i < 40; i++)
                  SizedBox(height: 60, child: Text('행 $i')),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

double _listOffset(WidgetTester tester) => tester
    .state<ScrollableState>(
      find.descendant(
        of: find.byType(ListView),
        matching: find.byType(Scrollable),
      ),
    )
    .position
    .pixels;

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

Future<void> _resizeTo(WidgetTester tester, Size size) async {
  setViewSize(tester, size);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('폰 폭(390)은 하단 탭 바, rail 없음', (tester) async {
    setViewSize(tester, const Size(390, 844));
    await tester.pumpWidget(const _ShellHarness());

    expect(find.byType(NavigationBar), findsOne);
    expect(find.byType(NavigationRail), findsNothing);
  });

  for (final width in [744.0, 1024.0, 1366.0]) {
    testWidgets('태블릿 폭($width)은 rail, 하단 탭 바 없음', (tester) async {
      setViewSize(tester, Size(width, 1024));
      await tester.pumpWidget(const _ShellHarness());

      expect(find.byType(NavigationRail), findsOne);
      expect(find.byType(NavigationBar), findsNothing);
      // 라벨까지 보인다 — 아이콘만 있는 rail 이 아니다.
      expect(find.text('오늘'), findsOne);
      expect(find.text('순위'), findsOne);
      expect(find.text('내 기록'), findsOne);
    });
  }

  testWidgets('rail 도 하단 탭 바와 같은 콜백으로 탭을 옮긴다', (tester) async {
    setViewSize(tester, const Size(1024, 768));
    await tester.pumpWidget(const _ShellHarness());

    await tester.tap(find.text('순위'));
    await tester.pumpAndSettle();
    expect(find.text('탭 1'), findsOne);

    await tester.tap(find.text('내 기록'));
    await tester.pumpAndSettle();
    expect(find.text('탭 2'), findsOne);
  });

  testWidgets('배너 슬롯은 rail 을 제외한 콘텐츠 열 하단에 앉는다', (tester) async {
    setViewSize(tester, const Size(1024, 768));
    await tester.pumpWidget(const _ShellHarness());

    final railWidth = tester.getSize(find.byType(NavigationRail)).width;
    final slot = tester.getRect(find.byType(AdBannerSlot));

    expect(railWidth, greaterThan(0));
    expect(slot.left, railWidth);
    expect(slot.width, 1024 - railWidth);
    expect(slot.bottom, 768);
  });

  testWidgets('폰 폭에서는 배너가 탭 바 아래, 화면 폭 전체다', (tester) async {
    setViewSize(tester, const Size(390, 844));
    await tester.pumpWidget(const _ShellHarness());

    final bar = tester.getRect(find.byType(NavigationBar));
    final slot = tester.getRect(find.byType(AdBannerSlot));

    expect(slot.top, greaterThanOrEqualTo(bar.bottom));
    expect(slot.width, 390);
  });

  testWidgets('회전·Split View: 폭이 390 → 744 → 390 이어도 탭·입력 텍스트·스크롤이 유지된다', (
    tester,
  ) async {
    setViewSize(tester, const Size(390, 844));
    await tester.pumpWidget(const _ShellHarness());

    await tester.tap(find.text('순위'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), '지하철역');
    await tester.drag(find.byType(ListView), const Offset(0, -200));
    await tester.pumpAndSettle();

    final offset = _listOffset(tester);
    expect(offset, greaterThan(0));
    expect(find.byType(NavigationBar), findsOne);

    // 태블릿 폭으로 (회전 / Split View 확대)
    await _resizeTo(tester, const Size(744, 1133));

    expect(find.byType(NavigationRail), findsOne);
    expect(find.byType(NavigationBar), findsNothing);
    expect(find.text('탭 1'), findsOne);
    expect(find.text('지하철역'), findsOne);
    expect(_listOffset(tester), offset);

    // 다시 폰 폭으로
    await _resizeTo(tester, const Size(390, 844));

    expect(find.byType(NavigationBar), findsOne);
    expect(find.byType(NavigationRail), findsNothing);
    expect(find.text('탭 1'), findsOne);
    expect(find.text('지하철역'), findsOne);
    expect(_listOffset(tester), offset);
  });

  // OVERRIDES §5: 배너는 하단 safe area **위**에 있어야 한다 — iPad 홈 인디케이터
  // 아래로 깔리면 광고가 가려지고 터치도 먹힌다.
  testWidgets('태블릿에서도 배너는 하단 safe area 위에 있다', (tester) async {
    tester.view.physicalSize = const Size(1024, 768);
    tester.view.devicePixelRatio = 1;
    tester.view.padding = const FakeViewPadding(bottom: 20);
    tester.view.viewPadding = const FakeViewPadding(bottom: 20);
    addTearDown(tester.view.reset);

    await tester.pumpWidget(const _ShellHarness());
    await tester.pumpAndSettle();

    expect(tester.getRect(find.byType(AdBannerSlot)).bottom, 768 - 20);
  });

  testWidgets('배너 슬롯이 없으면(구독자) 자리도 없다', (tester) async {
    setViewSize(tester, const Size(1024, 768));
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(Brightness.light),
        home: AdaptiveScaffold(
          selectedIndex: 0,
          onDestinationSelected: (_) {},
          destinations: const [
            AdaptiveDestination(icon: LucideIcons.grid, label: '오늘'),
            AdaptiveDestination(icon: LucideIcons.trophy, label: '순위'),
          ],
          body: const SizedBox.expand(),
        ),
      ),
    );

    expect(find.byType(AdBannerSlot), findsNothing);
    expect(find.byType(NavigationRail), findsOne);
  });
}
