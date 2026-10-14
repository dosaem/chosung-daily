import 'dart:async';

import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 내 기록 숫자(streak 3칸 · 오늘 탭 StreakBadge)의 정본은 서버 `/me/stats` 고,
/// 앱 시작 때 읽은 snapshot 이 그 첫 사본이다. 값이 null 이면 아직 시작이 끝나지
/// 않은 것이라 화면은 스켈레톤을 둔다.
///
/// 플레이 결과가 생기면 [refresh] 가 서버에서 다시 읽는다 — 시작 snapshot 은
/// 플레이 **전** 숫자라, 그걸 계속 보여주면 방금 올린 기록이 앱을 재시작할
/// 때까지 화면에 없다(US 14·16a).
class MyStatsNotifier extends AsyncNotifier<MyStats?> {
  /// 응답 경합을 끊는 세대 번호(`TodayPuzzleNotifier` 와 같은 방식).
  int _generation = 0;

  @override
  FutureOr<MyStats?> build() {
    // 시작을 다시 돌리면(스플래시 재시도) 그 응답이 다시 정본이 된다. 그때
    // 떠나 있던 재조회 응답은 이 번호로 버린다 — Riverpod 은 notifier 객체를
    // 그대로 두고 `build` 만 다시 부른다.
    _generation++;
    return ref.watch(startupStatsProvider);
  }

  /// 플레이 결과 뒤 서버에서 다시 읽는다. 실패하면 보던 숫자를 그대로 둔다 —
  /// 기록 숫자 하나 때문에 화면을 오류로 덮지 않는다(OVERRIDES §7).
  Future<void> refresh() async {
    final generation = ++_generation;
    final loaded = await AsyncValue.guard(
      ref.read(apiClientProvider).fetchMyStats,
    );
    if (!ref.mounted || generation != _generation) return;
    if (loaded case AsyncData(:final value)) state = AsyncData(value);
  }
}

final myStatsProvider = AsyncNotifierProvider<MyStatsNotifier, MyStats?>(
  MyStatsNotifier.new,
);
