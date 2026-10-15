import 'dart:async';

import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/guest/account_epoch.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// S4 7일 그리드의 데이터.
///
/// 값이 null 이면 **아직 모른다** 다(= 화면은 스켈레톤). 첫 조회 전과 계정이
/// 바뀐 직후가 그 상태다([discard]) — `MyStatsNotifier`·`TodayPuzzleNotifier`
/// 와 같은 방식이다. `FutureProvider` 로는 그 "버림" 을 표현할 수 없었다:
/// `ref.invalidate` 는 다시 읽는 동안 직전 값을 새 상태에 실어 주므로
/// (`AsyncValue.copyWithPrevious`) 화면이 옛 **계정**의 7일 칸을 계속 고른다.
class HistoryNotifier extends AsyncNotifier<List<HistoryDay>?> {
  /// 응답 경합을 끊는 세대 번호(`TodayPuzzleNotifier` 와 같은 방식).
  int _generation = 0;

  AccountEpochNotifier get _account => ref.read(accountEpochProvider.notifier);

  @override
  Future<List<HistoryDay>?> build() {
    final generation = ++_generation;
    return _initialLoad(generation);
  }

  /// 계정 경계(연결·전환·삭제 후 새 게스트)에서 **보던 7일 칸을 버리고** 새
  /// 계정의 것을 읽는다. 읽기가 실패하면 값이 없으므로 화면이 오류 줄 +
  /// 재시도를 세운다(OVERRIDES §7).
  Future<void> discard() async {
    final generation = ++_generation;
    state = const AsyncData<List<HistoryDay>?>(null);
    _commitLoad(await _load(), generation);
  }

  /// 7일 칸만 다시 읽는다(제출로 하루의 분류가 바뀐 경우). 보던 값이 있으면
  /// 스켈레톤으로 돌아가지 않고 조용히 바꿔 끼운다.
  Future<void> refresh() async {
    if (!ref.mounted) return;
    // 첫 조회가 아직 안 끝났으면 그 조회가 가져올 결과를 기다리면 된다
    // (`build` 가 돌려준 future 는 프레임워크가 직접 상태에 쓴다).
    if (state.isLoading && !state.hasValue) return;

    final generation = ++_generation;
    _commitLoad(await _load(), generation);
  }

  /// 오류 줄의 재시도 버튼. 처음부터 다시 돌린다(스켈레톤 → 결과).
  void retry() => ref.invalidateSelf();

  /// 계정 데이터를 읽는 조회는 공용 래퍼를 거친다 — 그 사이 계정이 바뀌면
  /// `null`("이 응답은 남의 것이다") 이 온다(D-29-6).
  Future<AsyncValue<List<HistoryDay>>?> _load() =>
      _account.fetchIfSameAccount(ref.read(apiClientProvider).fetchMyHistory);

  /// 첫 조회. `build` 가 돌려준 future 는 프레임워크가 [_commitLoad] 를
  /// 건너뛰고 바로 상태에 쓰므로, 버려야 하는 응답에는 지금 상태를 그대로
  /// 돌려준다([initialStateOrCurrent]).
  Future<List<HistoryDay>?> _initialLoad(int generation) async {
    final loaded = await _load();
    return initialStateOrCurrent<List<HistoryDay>?>(
      _canCommit(generation) ? loaded : null,
      () => ref.mounted ? state : const AsyncData<List<HistoryDay>?>(null),
    );
  }

  bool _canCommit(int generation) => ref.mounted && generation == _generation;

  /// [loaded] 가 null 이면 계정이 바뀐 뒤 도착한 **남의 응답**이다 — 지금
  /// 상태를 그대로 둔다.
  void _commitLoad(AsyncValue<List<HistoryDay>>? loaded, int generation) {
    if (loaded == null || !_canCommit(generation)) return;
    state = loaded;
  }
}

/// 계정 경계에서 보던 7일 칸을 버린다([HistoryNotifier.discard]).
///
/// 아직 아무도 읽지 않았으면 버릴 값도 없다 — 거기서 `read` 로 억지로 만들면
/// 보는 사람 없는 조회가 한 번 더 나간다(`discardTodayPuzzle` 과 같은 규칙).
void discardHistory(Ref ref) {
  if (!ref.exists(historyProvider)) return;
  unawaited(ref.read(historyProvider.notifier).discard());
}

/// 제출로 하루의 분류가 바뀌었으니 7일 칸만 다시 읽는다
/// ([HistoryNotifier.refresh]). 같은 이유로 **없으면 만들지 않는다** — 내 기록
/// 탭을 아직 안 열어 본 사용자에게 조회가 한 번 더 나가면 안 된다.
void refreshHistory(Ref ref) {
  if (!ref.exists(historyProvider)) return;
  unawaited(ref.read(historyProvider.notifier).refresh());
}

final historyProvider =
    AsyncNotifierProvider<HistoryNotifier, List<HistoryDay>?>(
      HistoryNotifier.new,
    );
