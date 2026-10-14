import 'package:chosung/routing/app_routes.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/widgets/ad_banner_slot.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// 하단 탭 3개 + 탭 바 아래 배너 슬롯(SCREENS "앱 탭 구조").
class HomeShell extends StatelessWidget {
  const HomeShell({required this.navigationShell, super.key});

  static const List<({String route, IconData icon, String labelKey})> _tabs = [
    (route: AppRoutes.today, icon: LucideIcons.grid, labelKey: 'tabs.today'),
    (
      route: AppRoutes.ranking,
      icon: LucideIcons.trophy,
      labelKey: 'tabs.ranking',
    ),
    (
      route: AppRoutes.records,
      icon: LucideIcons.calendar,
      labelKey: 'tabs.records',
    ),
  ];

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return Scaffold(
      body: navigationShell,
      // 탭 바와 배너를 통째로 하단 inset 위에 올린다 — 제스처 바 아래로 배너가
      // 깔리지 않게(OVERRIDES §5 "safe area 위에 고정").
      bottomNavigationBar: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              decoration: BoxDecoration(
                border: Border(top: BorderSide(color: colors.border)),
              ),
              child: NavigationBar(
                selectedIndex: navigationShell.currentIndex,
                onDestinationSelected: navigationShell.goBranch,
                destinations: [
                  for (final tab in _tabs)
                    NavigationDestination(
                      // 활성 탭은 brand 밑줄로 표시 — 면 채움·글자색 금지(OVERRIDES §2).
                      icon: Icon(tab.icon, color: colors.mutedForeground),
                      selectedIcon: _SelectedTabIcon(icon: tab.icon),
                      label: tab.labelKey.tr(),
                    ),
                ],
              ),
            ),
            // 구독자는 티켓 29·30 이 이 슬롯을 지운다. 그때까지는 항상 예약한다.
            const AdBannerSlot(),
          ],
        ),
      ),
    );
  }
}

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
