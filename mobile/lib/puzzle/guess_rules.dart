import 'package:chosung/api/api_models.dart';

/// 퍼즐 하나에 주는 기회. 서버 `MAX_ATTEMPTS`(app/services/game_rules.py)와 같다.
const int maxAttempts = 5;

/// 퍼즐이 바뀌는 시각의 시간대(KST, ADR 0001). 서머타임이 없어 고정 오프셋이다.
const Duration _kstOffset = Duration(hours: 9);

const Set<String> _separators = {' ', '-'};

/// 제출·표시에 쓰는 글자열. 서버 `normalize_for_compare` 와 같은 규칙이다 —
/// 구분자(공백·하이픈)를 빼고, en 은 대문자로 맞춘다.
///
/// 가림이 구분자를 타일이 아니라 타일 사이 간격으로 보여주기 때문에
/// (`app/utils/mask.py`) 플레이어에게 `Red Fox`·`red-fox`·`redfox` 는 같은
/// 답이고, 글자수 카운터("0/N")도 이 기준으로 세야 `length` 와 앞뒤가 맞는다.
String normalizeGuess(PuzzleLanguage language, String raw) {
  final letters = raw
      .trim()
      .split('')
      .where((ch) => !_separators.contains(ch))
      .join();
  return language == PuzzleLanguage.en ? letters.toUpperCase() : letters;
}

/// 제출 응답을 보드에 반영한다.
///
/// 보드의 정본은 서버 이력이다 — 앱을 껐다 켜면 `GET /puzzles/today` 의
/// `attempts` 로 다시 그린다. 그래도 제출 직후만큼은 응답으로 한 행을 쌓는다.
/// 같은 값을 받으려고 `GET` 을 한 번 더 때릴 이유가 없고(제출당 왕복 2회),
/// 응답은 그 한 행을 그리는 데 필요한 걸 이미 다 들고 있다.
TodayPuzzle applyGuess({
  required TodayPuzzle puzzle,
  required String guess,
  required GuessResult result,
}) {
  final letters = normalizeGuess(puzzle.language, guess);
  return puzzle.copyWith(
    attempts: [
      ...puzzle.attempts,
      PuzzleAttempt(
        guess: letters,
        // 정답 행은 서버가 feedback 을 안 보낸다 — 전부 맞음이라서다
        // (README "04. 시도 이력을 서버가 돌려주는 이유").
        feedback: result.feedback ?? List<bool>.filled(puzzle.length, true),
      ),
    ],
    attemptsLeft: result.attemptsLeft,
    status: switch (result) {
      GuessResult(isCorrect: true) => PuzzleStatus.success,
      GuessResult(attemptsLeft: 0) => PuzzleStatus.fail,
      _ => PuzzleStatus.inProgress,
    },
    // 3번째 오답에서 한 번 받은 힌트는 다음 응답에 없어도 화면에 남는다.
    hint: result.hint,
    answer: result.answer,
  );
}

/// 이 퍼즐에 쓴 시도 수. **보드 행 수가 아니라 서버가 준 남은 기회**로 센다 —
/// 끝난 퍼즐의 결과(공유 텍스트·분포의 내 위치)는 서버가 판정한 값이어야 한다
/// (웹 `buildShareText` 와 같은 기준).
int attemptsUsed(TodayPuzzle puzzle) => maxAttempts - puzzle.attemptsLeft;

/// 다음 KST 자정까지 남은 시간. 기기 시간대와 무관하게 같은 값이다.
Duration timeUntilNextPuzzle(DateTime now) {
  final kst = now.toUtc().add(_kstOffset);
  final nextMidnight = DateTime.utc(
    kst.year,
    kst.month,
    kst.day,
  ).add(const Duration(days: 1));
  return nextMidnight.difference(kst);
}

/// "07:12:33". 음수(이미 지난 시각)는 00:00:00 으로 눕힌다 — 자정 직후
/// 타이머와 서버 날짜가 몇 초 어긋나도 "-00:00:01" 이 보이지 않게.
String formatCountdown(Duration remaining) {
  final seconds = remaining.inSeconds < 0 ? 0 : remaining.inSeconds;
  String two(int value) => value.toString().padLeft(2, '0');
  return '${two(seconds ~/ 3600)}:${two(seconds ~/ 60 % 60)}'
      ':${two(seconds % 60)}';
}
