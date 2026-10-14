import 'dart:async';

import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/ads/ad_service.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 예약된 슬롯(`AdBannerSlot`) 안에서 배너 하나를 들고 있는다.
///
/// 폭은 **슬롯이 준 값**이다(rail 을 뺀 콘텐츠 열 폭, SCREENS T0). 회전·Split
/// View 로 폭이 바뀌면 새 폭으로 다시 로드한다 — 어댑티브 배너는 요청할 때의
/// 폭으로 크기가 정해지므로, 그대로 두면 넓어진 열에 옛 폭의 배너가 남는다.
///
/// 로드 전·실패 뒤에는 아무것도 그리지 않는다. 높이는 슬롯이 예약하고 있어서
/// 광고가 들어오거나 못 들어와도 레이아웃이 움직이지 않는다(OVERRIDES §5).
class BannerAdView extends ConsumerStatefulWidget {
  const BannerAdView({required this.width, super.key});

  final double width;

  @override
  ConsumerState<BannerAdView> createState() => _BannerAdViewState();
}

class _BannerAdViewState extends ConsumerState<BannerAdView> {
  LoadedBannerAd? _ad;

  /// 로드 요청의 세대. 폭이 빠르게 두 번 바뀌면 먼저 떠난 응답이 나중에
  /// 도착할 수 있어서, 자기 번호가 아직 최신일 때만 화면에 올린다.
  int _generation = 0;

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  @override
  void didUpdateWidget(BannerAdView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.width != widget.width) unawaited(_load());
  }

  @override
  void dispose() {
    unawaited(_ad?.dispose());
    super.dispose();
  }

  Future<void> _load() async {
    final generation = ++_generation;
    final previous = _ad;
    if (previous != null) {
      setState(() => _ad = null);
      unawaited(previous.dispose());
    }

    final loaded = await ref
        .read(adServiceProvider)
        .loadBanner(width: widget.width);
    if (!mounted || generation != _generation) {
      unawaited(loaded?.dispose());
      return;
    }
    setState(() => _ad = loaded);
  }

  @override
  Widget build(BuildContext context) => _ad?.view ?? const SizedBox.shrink();
}
