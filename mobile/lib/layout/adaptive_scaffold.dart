import 'package:chosung/layout/app_breakpoint.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:flutter/material.dart';

/// 탭 하나. 하단 탭 바와 rail 이 같은 목록을 쓴다 — 항목·순서·경로가 갈리면
/// 두 레이아웃에서 다른 앱이 된다.
class AdaptiveDestination {
  const AdaptiveDestination({required this.icon, required this.label});

  final IconData icon;
  final String label;
}

/// 폭에 따라 전역 내비게이션을 바꿔 끼우는 셸(SCREENS T0).
///
/// compact = 하단 `NavigationBar` + 탭 바 아래 배너, medium 이상 = 왼쪽
/// `NavigationRail` + 콘텐츠 열 하단 배너. 레이아웃만 바뀌고 [body] 는 같은
/// 위젯 트리로 남는다 — 그래서 회전·Split View 로 구간을 넘어가도 입력 중
/// 텍스트와 스크롤 위치가 살아 있다. 그걸 보장하는 게 아래 [_contentKey] 다:
/// `Row` 의 자식 수가 1 ↔ 2 로 바뀌어도 키가 같으면 Element 가 재사용된다.
class AdaptiveScaffold extends StatelessWidget {
  const AdaptiveScaffold({
    required this.destinations,
    required this.selectedIndex,
    required this.onDestinationSelected,
    required this.body,
    this.banner,
    super.key,
  });

  static const ValueKey<String> _contentKey = ValueKey('adaptive-content');

  final List<AdaptiveDestination> destinations;
  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;
  final Widget body;

  /// 배너 광고 슬롯. 구독자는 null 이라 자리 자체가 없다(OVERRIDES §5).
  final Widget? banner;

  @override
  Widget build(BuildContext context) {
    final hasRail = AppBreakpoint.of(context).hasRail;
    final slot = banner;

    final content = Expanded(
      key: _contentKey,
      // 콘텐츠를 자기 시맨틱스 컨테이너로 감싼다. 안쪽 go_router 분기
      // Navigator 의 라우트 배리어가 `BlockSemantics` 를 들고 있어서, 그냥 두면
      // **먼저 그려진 rail 의 시맨틱스까지 통째로 지운다**(스크린 리더가 탭을
      // 못 읽는다). 컨테이너가 그 지우기를 콘텐츠 안으로 가둔다.
      child: Semantics(
        container: true,
        child: Column(
          children: [
            Expanded(child: body),
            // 배너는 rail 아래가 아니라 콘텐츠 열 하단, safe area 위다.
            if (hasRail && slot != null) SafeArea(top: false, child: slot),
          ],
        ),
      ),
    );

    return Scaffold(
      body: Row(
        children: [
          if (hasRail)
            _Rail(
              destinations: destinations,
              selectedIndex: selectedIndex,
              onDestinationSelected: onDestinationSelected,
            ),
          content,
        ],
      ),
      bottomNavigationBar: hasRail
          ? null
          : _BottomBar(
              destinations: destinations,
              selectedIndex: selectedIndex,
              onDestinationSelected: onDestinationSelected,
              banner: slot,
            ),
    );
  }
}

class _Rail extends StatelessWidget {
  const _Rail({
    required this.destinations,
    required this.selectedIndex,
    required this.onDestinationSelected,
  });

  final List<AdaptiveDestination> destinations;
  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border(right: BorderSide(color: colors.border)),
      ),
      child: SafeArea(
        right: false,
        child: NavigationRail(
          selectedIndex: selectedIndex,
          onDestinationSelected: onDestinationSelected,
          backgroundColor: colors.background,
          labelType: NavigationRailLabelType.all,
          // Material 기본 선택 표시는 면을 채운다 — OVERRIDES §2 가 금지해서
          // 끄고 아이콘 + brand 밑줄(_SelectedTabIcon)로만 알린다.
          useIndicator: false,
          destinations: [
            for (final destination in destinations)
              NavigationRailDestination(
                icon: Icon(destination.icon, color: colors.mutedForeground),
                selectedIcon: _SelectedTabIcon(icon: destination.icon),
                label: Text(destination.label),
              ),
          ],
        ),
      ),
    );
  }
}

class _BottomBar extends StatelessWidget {
  const _BottomBar({
    required this.destinations,
    required this.selectedIndex,
    required this.onDestinationSelected,
    required this.banner,
  });

  final List<AdaptiveDestination> destinations;
  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;
  final Widget? banner;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final slot = banner;

    // 탭 바와 배너를 통째로 하단 inset 위에 올린다 — 제스처 바 아래로 배너가
    // 깔리지 않게(OVERRIDES §5 "safe area 위에 고정").
    return SafeArea(
      top: false,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          DecoratedBox(
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: colors.border)),
            ),
            child: NavigationBar(
              selectedIndex: selectedIndex,
              onDestinationSelected: onDestinationSelected,
              destinations: [
                for (final destination in destinations)
                  NavigationDestination(
                    icon: Icon(destination.icon, color: colors.mutedForeground),
                    selectedIcon: _SelectedTabIcon(icon: destination.icon),
                    label: destination.label,
                  ),
              ],
            ),
          ),
          ?slot,
        ],
      ),
    );
  }
}

/// 활성 탭은 brand 밑줄로 표시 — 면 채움·글자색 금지(OVERRIDES §2).
class _SelectedTabIcon extends StatelessWidget {
  const _SelectedTabIcon({required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: colors.foreground),
        const SizedBox(height: 2),
        Container(width: 16, height: 2, color: colors.brand),
      ],
    );
  }
}
