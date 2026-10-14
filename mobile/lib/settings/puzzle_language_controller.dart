import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/guest/account_epoch.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/ranking/leaderboard_controller.dart';
import 'package:chosung/records/my_stats_controller.dart';
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

  /// 지금 보고 있는 언어가 **어느 계정의** 값인가([accountEpochProvider]).
  /// 쓰기는 이 값과 지금 계정을 비교한다 — 계정이 바뀐 뒤의 탭은 새 계정의
  /// 언어를 옛 계정 화면에서 고른 값으로 덮어쓴다(D-29-5 와 같은 장치).
  int _accountEpoch = 0;

  @override
  PuzzleLanguageSetting build() {
    // `/me/stats` 를 다시 읽으면(시작 재시도·계정 전환) 서버 값이 다시
    // 정본이 된다. 그때 떠나 있던 쓰기 응답은 이 번호로 버린다.
    //
    // 시작 snapshot(`startupStatsProvider`) 이 아니라 그 사본을 들고 있는
    // `myStatsProvider` 를 본다(티켓 29) — 계정을 전환하면 새 계정의
    // `puzzle_language` 가 여기로 들어오고, 안 그러면 설정 행만 옛 계정
    // 값으로 남는다.
    _generation++;
    _accountEpoch = ref.read(accountEpochProvider);
    return PuzzleLanguageSetting(
      language:
          ref.watch(myStatsProvider).value?.puzzleLanguage ?? PuzzleLanguage.ko,
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
      // 이 행의 값은 지금 계정의 `/me/stats` 에서 왔다 — 그 사이 계정이
      // 바뀌었으면 새 계정의 언어를 옛 계정 화면에서 고른 값으로 덮어쓰지
      // 않는다(D-29-5 와 같은 장치). 다시 빌드되면 새 계정 값이 들어온다.
      final applied = await ref
          .read(accountEpochProvider.notifier)
          .sendIfSameAccount(
            _accountEpoch,
            () => ref.read(apiClientProvider).updatePuzzleLanguage(language),
          );
      if (applied == null) {
        if (_canCommit(generation)) {
          state = PuzzleLanguageSetting(language: previous);
        }
        return false;
      }
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
