import 'dart:async';

import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/clock.dart';
import 'package:chosung/guest/account_epoch.dart';
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

  /// 지금 들고 있는 값을 **가져온 조회가 언제 떠났는가**(티켓 33). null 은
  /// "방금 받았다" 다 — 시작 응답과 이미 읽어 둔 값([adopt])이 그렇다.
  ///
  /// 이 응답에는 기록 숫자만 아니라 구독 권한(`entitlement`)도 실려 오고,
  /// 그 권한을 `entitlementProvider` 에 넣을 때 **얼마나 묵은 사실인가**를
  /// 같이 넘겨야 한다. 떠난 조회가 돌아오는 사이에 구매(32)가 권한을
  /// 넣었으면 구매 **전** 사실로 그걸 덮으면 안 된다. 떠난 시각을 부른 쪽이
  /// 들고 있으면 조회가 둘 겹칠 때 먼저 풀린 쪽이 그 칸을 비워버리고
  /// (D-33-1), 이 provider 를 직접 부르는 경로(플레이 결과 재조회 25·26)는
  /// 아예 시각이 없다(D-33-2) — 그래서 **커밋하는 자리**에서 찍는다.
  DateTime? _observedAt;

  /// [MyStatsNotifier] 가 지금 들고 있는 값의 관측 시각. null = "방금".
  DateTime? get observedAt => _observedAt;

  AccountEpochNotifier get _account => ref.read(accountEpochProvider.notifier);

  @override
  FutureOr<MyStats?> build() {
    // 시작을 다시 돌리면(스플래시 재시도) 그 응답이 다시 정본이 된다. 그때
    // 떠나 있던 재조회 응답은 이 번호로 버린다 — Riverpod 은 notifier 객체를
    // 그대로 두고 `build` 만 다시 부른다.
    _generation++;
    // 시작 응답은 스플래시가 방금 받은 값이다.
    _observedAt = null;
    return ref.watch(startupStatsProvider);
  }

  /// 플레이 결과 뒤 서버에서 다시 읽는다. 실패하면 보던 숫자를 그대로 둔다 —
  /// 기록 숫자 하나 때문에 화면을 오류로 덮지 않는다(OVERRIDES §7).
  Future<void> refresh() async {
    final generation = ++_generation;
    // 지역 변수다 — 조회마다 **자기** 떠난 시각을 들고 간다(D-33-1).
    final departedAt = ref.read(clockProvider)();
    final loaded = await _account.fetchIfSameAccount(
      ref.read(apiClientProvider).fetchMyStats,
    );
    // null 이면 계정이 바뀐 뒤 도착한 남의 숫자다 — 지금 값을 그대로 둔다.
    if (loaded == null || !ref.mounted || generation != _generation) return;
    if (loaded case AsyncData(:final value)) {
      // 커밋하는 조회만 관측 시각을 남긴다 — 세대에 밀려 버려진 조회가
      // 이 칸을 건드리면 다음 응답이 남의 시각으로 들어간다.
      _observedAt = departedAt;
      state = AsyncData(value);
    }
  }

  /// 보던 숫자를 **버린다**. [refresh] 와 반대로 쓰는 자리가 따로 있다:
  /// 계정 경계가 바뀌면(연결·전환·삭제) 옛 계정 값은 오래된 사본이 아니라
  /// 아예 **다른 사람의 값**이다. 그대로 두면 카드가 보여주는 계정과 토큰이
  /// 가리키는 계정이 갈라지고, 그 화면에서 누른 삭제가 다른 계정을 지운다.
  /// 값이 null 이면 화면은 스켈레톤이다 — 이 provider 의 "아직 모른다" 는
  /// 원래 그 뜻이다(시작이 끝나기 전 상태). `AsyncLoading`·`AsyncError` 로
  /// 눕히면 안 된다: Riverpod 이 새 상태에 직전 값을 실어 주므로
  /// (`AsyncValue.copyWithPrevious`) `value` 로 옛 계정이 되살아난다.
  void discard() {
    _generation++;
    _observedAt = null;
    state = const AsyncData<MyStats?>(null);
  }

  /// 새 계정의 숫자를 앉힌다. [stats] 를 이미 읽어 뒀으면(백업 코드 확인
  /// 응답) 그걸 쓰고, 없으면 새 토큰으로 읽는다.
  ///
  /// 읽기가 실패하면 옛 계정 값을 되살리지 않고([discard] 한 그대로) 예외를
  /// 올린다 — 부른 쪽(`AccountNotifier`)이 그 일을 시작한 자리에 실패 문구를
  /// 둬야 사용자가 다시 시도할 수 있다(OVERRIDES §7).
  Future<void> adopt(MyStats? stats) async {
    discard();
    final generation = _generation;
    if (stats != null) {
      // 부른 쪽이 방금 받은 응답이다 — 관측 시각은 "지금"(null).
      state = AsyncData(stats);
      return;
    }

    final departedAt = ref.read(clockProvider)();
    final loaded = await _account.fetchIfSameAccount(
      ref.read(apiClientProvider).fetchMyStats,
    );
    if (loaded == null || !ref.mounted || generation != _generation) return;
    switch (loaded) {
      case AsyncData(:final value):
        _observedAt = departedAt;
        state = AsyncData(value);
      case AsyncError(:final error, :final stackTrace):
        Error.throwWithStackTrace(error, stackTrace);
      case _:
    }
  }
}

final myStatsProvider = AsyncNotifierProvider<MyStatsNotifier, MyStats?>(
  MyStatsNotifier.new,
);
