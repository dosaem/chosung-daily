import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/ranking/leaderboard_controller.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 지금 고른 퍼즐 언어. 서버(`Guest.puzzle_language`)가 정본이고 여기는 그
/// 사본이다 — 시작할 때 읽은 `/me/stats` 로 시작하고, S4 설정이 `PATCH /me` 로
/// 바꾼다. 앱 UI 언어(easy_localization)와는 별개다.
class PuzzleLanguageNotifier extends Notifier<PuzzleLanguage> {
  @override
  PuzzleLanguage build() =>
      // `/me/stats` 를 다시 읽으면(시작 재시도) 서버 값이 다시 정본이 된다.
      ref.watch(startupStatsProvider)?.puzzleLanguage ?? PuzzleLanguage.ko;

  /// 언어를 바꾼다. 성공하면 true — 실패는 설정 화면이 그 행 아래 한 줄로
  /// 알린다(토스트로 숨기지 않는다, OVERRIDES §7).
  Future<bool> change(PuzzleLanguage language) async {
    if (language == state) return true;

    try {
      state = await ref.read(apiClientProvider).updatePuzzleLanguage(language);
    } on ApiException {
      return false;
    }
    // 오늘 퍼즐도 리더보드도 언어마다 다른 데이터다. 보던 걸 바꿔 끼우는 게
    // 아니라 다른 퍼즐을 처음부터 읽는 것이라 스켈레톤부터 다시 간다.
    ref
      ..invalidate(todayPuzzleProvider)
      ..invalidate(leaderboardProvider);
    return true;
  }
}

final puzzleLanguageProvider =
    NotifierProvider<PuzzleLanguageNotifier, PuzzleLanguage>(
      PuzzleLanguageNotifier.new,
    );
