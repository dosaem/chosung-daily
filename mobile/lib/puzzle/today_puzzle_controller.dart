import 'dart:async';

import 'package:chosung/api/api_client.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/puzzle/guess_rules.dart';
import 'package:chosung/puzzle/today_puzzle_state.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// S1 오늘 탭의 상태. `GET /puzzles/today` 하나가 보드의 정본이다 —
/// 로컬에 시도 이력을 쌓지 않는다(README "04. 시도 이력을 서버가 돌려주는 이유").
class TodayPuzzleNotifier extends AsyncNotifier<TodayState> {
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

  /// 포그라운드 복귀·알림 탭. 이미 보드가 있으면 스켈레톤으로 돌아가지 않고
  /// 조용히 바꿔 끼운다 — 복귀마다 화면이 깜빡이면 멀쩡한 보드를 잃는다.
  Future<void> refresh() async {
    state = await AsyncValue.guard(_load);
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

    state = AsyncData(TodayPuzzleReady(puzzle: puzzle, submitting: true));

    try {
      final result = await _api.submitGuess(
        puzzleId: puzzle.puzzleId,
        guess: guess,
      );
      state = AsyncData(
        TodayPuzzleReady(
          puzzle: applyGuess(puzzle: puzzle, guess: guess, result: result),
        ),
      );
      return true;
    } on PuzzleChangedApiException {
      // 시도는 소비되지 않았다. 새 퍼즐을 읽어와 그 위에 메시지를 올린다.
      final reloaded = await AsyncValue.guard(_load);
      state = reloaded.whenData(
        (value) => switch (value) {
          TodayPuzzleReady(:final puzzle) => TodayPuzzleReady(
            puzzle: puzzle,
            notice: TodayNotice.puzzleChanged,
          ),
          TodayNoPuzzle() => value,
        },
      );
      return false;
    } on NetworkApiException {
      state = AsyncData(
        TodayPuzzleReady(puzzle: puzzle, notice: TodayNotice.offline),
      );
      return false;
    } on ApiException {
      state = AsyncData(
        TodayPuzzleReady(puzzle: puzzle, notice: TodayNotice.submitFailed),
      );
      return false;
    }
  }
}

final todayPuzzleProvider =
    AsyncNotifierProvider<TodayPuzzleNotifier, TodayState>(
      TodayPuzzleNotifier.new,
    );
