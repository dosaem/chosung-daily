import 'dart:async';

import 'package:chosung/api/api_client.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/puzzle/guess_rules.dart';
import 'package:chosung/puzzle/today_puzzle_state.dart';
import 'package:chosung/ranking/leaderboard_controller.dart';
import 'package:chosung/records/history_controller.dart';
import 'package:chosung/records/my_stats_controller.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// S1 오늘 탭의 상태. `GET /puzzles/today` 하나가 보드의 정본이다 —
/// 로컬에 시도 이력을 쌓지 않는다(README "04. 시도 이력을 서버가 돌려주는 이유").
class TodayPuzzleNotifier extends AsyncNotifier<TodayState> {
  /// 응답 경합을 끊는 세대 번호. 조회·제출은 **떠날 때** 이 번호를 올리고,
  /// 응답이 돌아오면 자기 번호가 아직 최신일 때만 상태에 쓴다. 먼저 떠난 느린
  /// 응답이 나중에 도착해 새 보드를 과거로 되돌리는 걸 막는다.
  int _generation = 0;

  /// 제출 응답을 기다리는 중인가. 그 사이의 재조회는 보드를 건드리지 않고
  /// [_refreshQueued] 로 미룬다 — 지금 읽는 서버 이력엔 방금 보낸 답이 아직
  /// 없어서, 그대로 쓰면 제출한 행이 사라지고 제출 잠금까지 풀려 같은 답이
  /// 두 번 들어간다.
  bool _submitting = false;
  bool _refreshQueued = false;

  ApiClient get _api => ref.read(apiClientProvider);

  @override
  Future<TodayState> build() {
    // 앱 시작(= 이 provider 의 첫 빌드)과 포그라운드 복귀 때 다시 읽는다.
    // 복귀 감지를 탭 위젯이 아니라 여기에 두는 이유: 복귀 순간 사용자가 순위·
    // 기록 탭에 있을 수 있고, 그때도 오늘 보드는 새 것이어야 한다. 알림 탭으로
    // 들어오는 경로(티켓 30)도 같은 [refresh] 를 다시 쓴다.
    final lifecycle = AppLifecycleListener(
      onResume: () => unawaited(refresh()),
    );
    ref.onDispose(lifecycle.dispose);
    // 다시 빌드되는 것(= `retry()` 의 `invalidateSelf`)도 상태를 바꾸는 사건이다.
    // Riverpod 은 notifier 객체를 그대로 두고 `build` 만 다시 부르므로 세대를
    // 여기서 올리지 않으면 이전 빌드에서 떠난 응답이 새 보드에 그대로 쓰인다.
    _generation++;
    return _load();
  }

  Future<TodayState> _load() async {
    try {
      return TodayPuzzleReady(puzzle: await _api.fetchTodayPuzzle());
    } on NoPuzzleTodayApiException {
      // 오류가 아니라 "아직" 이다 — 카운트다운 카드로 보여준다(OVERRIDES §7).
      return const TodayNoPuzzle();
    }
  }

  /// 오류 카드의 재시도 버튼. 처음부터 다시 돌린다(스켈레톤 → 결과).
  void retry() => ref.invalidateSelf();

  /// 포그라운드 복귀·알림 탭·보드의 인라인 재시도. 이미 보드가 있으면
  /// 스켈레톤으로 돌아가지 않고 조용히 바꿔 끼운다 — 복귀마다 화면이 깜빡이면
  /// 멀쩡한 보드를 잃는다.
  Future<void> refresh() async {
    if (!ref.mounted) return;
    if (_submitting) {
      _refreshQueued = true;
      return;
    }
    // 첫 조회가 아직 안 끝났으면 그 조회가 가져올 결과를 기다리면 된다.
    // (`build` 가 돌려준 future 는 프레임워크가 직접 상태에 쓰기 때문에 세대
    // 검사로 버릴 수 없다 — 그래서 두 번째 조회를 아예 띄우지 않는다.)
    if (state.isLoading && !state.hasValue) return;

    final generation = ++_generation;
    _commitLoad(await AsyncValue.guard(_load), generation);
  }

  /// 답을 제출한다. 보드에 한 행이 쌓였으면 true — 그때만 화면이 입력창을 비운다.
  Future<bool> submit(String raw) async {
    final current = state.value;
    if (current is! TodayPuzzleReady) return false;

    final puzzle = current.puzzle;
    final guess = normalizeGuess(puzzle.language, raw);
    // 길이가 안 맞는 제출은 서버에서도 시도를 소비하지 않는다(400). 왕복을
    // 아끼려고가 아니라, 제출 버튼이 잠겨 있어야 할 상태를 한 곳에서 판정한다.
    if (puzzle.status.isFinished ||
        current.submitting ||
        guess.length != puzzle.length) {
      return false;
    }

    final generation = ++_generation;
    _submitting = true;
    state = AsyncData(TodayPuzzleReady(puzzle: puzzle, submitting: true));

    try {
      final result = await _api.submitGuess(
        puzzleId: puzzle.puzzleId,
        guess: guess,
      );
      if (!_canCommit(generation)) return false;
      final played = applyGuess(puzzle: puzzle, guess: guess, result: result);
      state = AsyncData(TodayPuzzleReady(puzzle: played));
      if (played.status.isFinished) _invalidateDayResultReaders();
      return true;
    } on PuzzleChangedApiException {
      // 시도는 소비되지 않았다. 새 퍼즐을 읽어와 그 위에 메시지를 올린다.
      _commitLoad(
        await AsyncValue.guard(_load),
        generation,
        notice: TodayNotice.puzzleChanged,
      );
      return false;
    } on NetworkApiException {
      _commitNotice(generation, puzzle, TodayNotice.offline);
      return false;
    } on ApiException {
      _commitNotice(generation, puzzle, TodayNotice.submitFailed);
      return false;
    } finally {
      _submitting = false;
      if (_refreshQueued) {
        _refreshQueued = false;
        // 제출 중 미뤄둔 복귀 재조회. 제출 결과를 쓴 뒤에 돌리므로 서버 보드가
        // 마지막 말이 된다(US 3a·3b).
        unawaited(refresh());
      }
    }
  }

  /// 오늘 결과가 확정되면 그 결과로 바뀌는 다른 화면의 데이터를 버린다 —
  /// 순위(S3)와 7일 기록·streak(S4)이다. 탭을 유지하는 셸에서는 탭을 다시 열어도
  /// 위젯만 다시 보이고 provider 는 그대로라, 여기서 알려주지 않으면 방금 올린
  /// 기록이 앱을 재시작할 때까지 어디에도 안 나온다(US 12·14·16a·16b).
  ///
  /// 끝나지 않은 시도 한 줄로는 부르지 않는다 — 순위는 푼 사람만 올라가고 7일
  /// 칸·누적·streak 도 끝난 뒤에 바뀌어서, 매 제출마다 세 번을 다시 읽을 이유가
  /// 없다.
  void _invalidateDayResultReaders() {
    ref
      ..invalidate(leaderboardProvider)
      ..invalidate(historyProvider);
    // streak 은 무효화가 아니라 재조회다 — 다시 빌드하면 플레이 전 시작
    // snapshot 으로 돌아간다.
    unawaited(ref.read(myStatsProvider.notifier).refresh());
  }

  /// 이 응답을 아직 상태에 써도 되는가. 그 사이 provider 가 버려졌거나(재시도)
  /// 더 새 요청이 떠났으면 버린다.
  bool _canCommit(int generation) => ref.mounted && generation == _generation;

  /// 보드는 그대로 두고 그 위에 안내 한 줄만 올린다(제출 실패 경로).
  void _commitNotice(int generation, TodayPuzzle puzzle, TodayNotice notice) {
    if (!_canCommit(generation)) return;
    state = AsyncData(TodayPuzzleReady(puzzle: puzzle, notice: notice));
  }

  /// 조회 결과를 상태에 올린다.
  ///
  /// 실패했을 때 **보고 있던 보드는 지우지 않고** 그 자리에 안내 한 줄 + 재시도를
  /// 남긴다(US 8, OVERRIDES §7). 오류를 `AsyncError` 로만 두면 Riverpod 이
  /// 이전 값을 같이 들고 있어(`copyWithPrevious`) 화면은 보드를 고르고, 오류는
  /// 아무도 안 보는 곳에 남아 재조회가 실패한 걸 알 방법이 없어진다.
  void _commitLoad(
    AsyncValue<TodayState> loaded,
    int generation, {
    TodayNotice? notice,
  }) {
    if (!_canCommit(generation)) return;

    if (loaded case AsyncError(:final error)) {
      final previous = state.value;
      if (previous is TodayPuzzleReady) {
        state = AsyncData(
          TodayPuzzleReady(
            puzzle: previous.puzzle,
            notice: error is NetworkApiException
                ? TodayNotice.offline
                : TodayNotice.refreshFailed,
          ),
        );
        return;
      }
      // 보드가 없으면 오류 카드가 받는다(스켈레톤 → 오류).
      state = loaded;
      return;
    }

    state = loaded.whenData(
      (value) => switch ((value, notice)) {
        (TodayPuzzleReady(:final puzzle), final TodayNotice notice) =>
          TodayPuzzleReady(puzzle: puzzle, notice: notice),
        _ => value,
      },
    );
  }
}

final todayPuzzleProvider =
    AsyncNotifierProvider<TodayPuzzleNotifier, TodayState>(
      TodayPuzzleNotifier.new,
    );
