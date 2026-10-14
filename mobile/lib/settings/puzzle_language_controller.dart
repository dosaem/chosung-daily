import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/ranking/leaderboard_controller.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 지금 고른 퍼즐 언어와 "바꾸는 중" 여부.
@immutable
class PuzzleLanguageSetting {
  const PuzzleLanguageSetting({required this.language, this.changing = false});

  final PuzzleLanguage language;

  /// `PATCH /me` 응답을 기다리는 중. 그 동안 설정 행은 눌리지 않는다 —
  /// 쓰기를 직렬화하는 가장 단순한 방법이고, 두 번 눌러 서버와 화면이 서로
  /// 다른 언어로 끝나는 경우를 아예 만들지 않는다.
  final bool changing;
}

/// 퍼즐 언어의 정본은 서버(`Guest.puzzle_language`)고 여기는 그 사본이다 —
/// 시작할 때 읽은 `/me/stats` 로 시작하고, S4 설정이 `PATCH /me` 로 바꾼다.
/// 앱 UI 언어(easy_localization)와는 별개다.
class PuzzleLanguageNotifier extends Notifier<PuzzleLanguageSetting> {
  /// 응답 경합을 끊는 세대 번호(티켓 25 `TodayPuzzleNotifier` 와 같은 방식).
  /// 쓰기는 떠날 때 번호를 올리고, 응답이 돌아오면 자기 번호가 아직 최신일
  /// 때만 상태에 쓴다.
  int _generation = 0;

  @override
  PuzzleLanguageSetting build() {
    // `/me/stats` 를 다시 읽으면(시작 재시도) 서버 값이 다시 정본이 된다.
    // 그때 떠나 있던 쓰기 응답은 이 번호로 버린다.
    _generation++;
    return PuzzleLanguageSetting(
      language:
          ref.watch(startupStatsProvider)?.puzzleLanguage ?? PuzzleLanguage.ko,
    );
  }

  /// 언어를 바꾼다. 성공하면 true — 실패는 설정 화면이 그 행 아래 한 줄로
  /// 알린다(토스트로 숨기지 않는다, OVERRIDES §7).
  Future<bool> change(PuzzleLanguage language) async {
    if (state.changing || language == state.language) return true;

    final generation = ++_generation;
    final previous = state.language;
    state = PuzzleLanguageSetting(language: previous, changing: true);

    try {
      final applied = await ref
          .read(apiClientProvider)
          .updatePuzzleLanguage(language);
      if (!_canCommit(generation)) return false;
      state = PuzzleLanguageSetting(language: applied);
      // 오늘 퍼즐도 리더보드도 언어마다 다른 데이터다. 보던 걸 바꿔 끼우는 게
      // 아니라 다른 퍼즐을 처음부터 읽는 것이라 스켈레톤부터 다시 간다.
      ref
        ..invalidate(todayPuzzleProvider)
        ..invalidate(leaderboardProvider);
      return true;
    } on ApiException {
      if (_canCommit(generation)) {
        state = PuzzleLanguageSetting(language: previous);
      }
      return false;
    }
  }

  /// 이 응답을 아직 상태에 써도 되는가 — 그 사이 다시 빌드됐으면 버린다.
  bool _canCommit(int generation) => ref.mounted && generation == _generation;
}

final puzzleLanguageProvider =
    NotifierProvider<PuzzleLanguageNotifier, PuzzleLanguageSetting>(
      PuzzleLanguageNotifier.new,
    );
