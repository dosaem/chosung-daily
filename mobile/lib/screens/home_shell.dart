import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/ads/banner_ad_view.dart';
import 'package:chosung/layout/adaptive_scaffold.dart';
import 'package:chosung/widgets/ad_banner_slot.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// 탭 3개를 [AdaptiveScaffold] 에 넘긴다 — 폭에 따라 하단 탭 바와 rail 중
/// 어느 쪽으로 보일지는 그쪽이 정한다(SCREENS "앱 탭 구조"·T0).
///
/// 순서는 `app_router.dart` 의 `StatefulShellBranch` 순서와 같아야 한다 —
/// `goBranch` 가 인덱스로 분기를 고르므로 두 목록이 어긋나면 엉뚱한 탭이 열린다.
class HomeShell extends ConsumerWidget {
  const HomeShell({required this.navigationShell, super.key});

  static const List<({IconData icon, String labelKey})> _tabs = [
    (icon: LucideIcons.grid, labelKey: 'tabs.today'),
    (icon: LucideIcons.trophy, labelKey: 'tabs.ranking'),
    (icon: LucideIcons.calendar, labelKey: 'tabs.records'),
  ];

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final gate = ref.watch(adGateProvider);

    return AdaptiveScaffold(
      selectedIndex: navigationShell.currentIndex,
      onDestinationSelected: navigationShell.goBranch,
      destinations: [
        for (final tab in _tabs)
          AdaptiveDestination(icon: tab.icon, label: tab.labelKey.tr()),
      ],
      // 구독자는 슬롯 자체가 없고 콘텐츠가 그 자리를 채운다(US 31). 광고를
      // 못 띄우는 상태(동의 전·조회 실패)에서는 자리만 비워 둔다 — 그래야
      // 동의가 끝나고 배너가 들어올 때 화면이 튀지 않는다(OVERRIDES §5).
      banner: gate.showsBannerSlot
          ? AdBannerSlot(
              builder: gate.canLoadAds
                  ? (context, bannerWidth) => BannerAdView(width: bannerWidth)
                  : null,
            )
          : null,
      body: navigationShell,
    );
  }
}
