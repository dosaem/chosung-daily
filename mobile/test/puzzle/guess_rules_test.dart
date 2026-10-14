import 'package:chosung/api/api_models.dart';
import 'package:chosung/puzzle/guess_rules.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';

void main() {
  group('normalizeGuess', () {
    // 서버 `normalize_for_compare`(app/services/game_rules.py)와 같은 규칙이다 —
    // 가림이 구분자를 간격으로 보여주니 플레이어는 띄어 쓰든 안 쓰든 같은 답을 친다.
    test('구분자(공백·하이픈)를 빼고 en 은 대문자로 맞춘다', () {
      expect(
        normalizeGuess(PuzzleLanguage.en, ' harry-potter '),
        'HARRYPOTTER',
      );
      expect(normalizeGuess(PuzzleLanguage.en, 'HARRY POTTER'), 'HARRYPOTTER');
    });

    test('ko 는 대소문자를 건드리지 않는다', () {
      expect(normalizeGuess(PuzzleLanguage.ko, ' 지하철 역 '), '지하철역');
    });
  });

  group('applyGuess', () {
    final puzzle = fakeTodayPuzzle();

    test('오답은 피드백 그대로 한 행이 쌓이고 남은 기회가 줄어든다', () {
      final next = applyGuess(
        puzzle: puzzle,
        guess: '지하촌역',
        result: const GuessResult(
          isCorrect: false,
          attemptsLeft: 4,
          feedback: [true, false, false, true],
        ),
      );

      expect(next.attempts.single.guess, '지하촌역');
      expect(next.attempts.single.feedback, [true, false, false, true]);
      expect(next.attemptsLeft, 4);
      expect(next.status, PuzzleStatus.inProgress);
    });

    // 서버는 정답일 때 feedback 을 안 보낸다 — 그 행은 전부 맞음이다.
    test('정답은 feedback 을 전부 true 로 채우고 success 가 된다', () {
      final next = applyGuess(
        puzzle: puzzle,
        guess: '지하철역',
        result: const GuessResult(
          isCorrect: true,
          attemptsLeft: 4,
          answer: '지하철역',
        ),
      );

      expect(next.attempts.single.feedback, [true, true, true, true]);
      expect(next.status, PuzzleStatus.success);
      expect(next.answer, '지하철역');
    });

    test('기회를 다 쓴 오답은 fail 이 되고 정답을 받아 둔다', () {
      final next = applyGuess(
        puzzle: puzzle.copyWith(attemptsLeft: 1),
        guess: '지하촌역',
        result: const GuessResult(
          isCorrect: false,
          attemptsLeft: 0,
          feedback: [true, false, false, true],
          answer: '지하철역',
        ),
      );

      expect(next.status, PuzzleStatus.fail);
      expect(next.answer, '지하철역');
    });

    test('en 은 정규화된 글자열이 보드 행으로 들어간다', () {
      final next = applyGuess(
        puzzle: fakeTodayPuzzle(
          language: PuzzleLanguage.en,
          mask: const [
            MaskTile(type: MaskTileType.revealed, char: 'R'),
            MaskTile(type: MaskTileType.hidden, char: ''),
            MaskTile(type: MaskTileType.revealed, char: 'D'),
            MaskTile(type: MaskTileType.separator, char: ' '),
            MaskTile(type: MaskTileType.revealed, char: 'F'),
            MaskTile(type: MaskTileType.hidden, char: ''),
            MaskTile(type: MaskTileType.revealed, char: 'X'),
          ],
        ),
        guess: 'red fox',
        result: const GuessResult(
          isCorrect: false,
          attemptsLeft: 4,
          feedback: [true, true, true, true, false, true],
        ),
      );

      expect(next.attempts.single.guess, 'REDFOX');
    });

    // 3번째 오답 뒤 서버가 힌트를 같이 보낸다. 그 다음 응답에 힌트가 없어도
    // 화면에서 사라지면 안 된다.
    test('한 번 받은 힌트는 다음 제출 응답에 없어도 남는다', () {
      final withHint = applyGuess(
        puzzle: puzzle,
        guess: '지하촌역',
        result: const GuessResult(
          isCorrect: false,
          attemptsLeft: 2,
          feedback: [true, false, false, true],
          hint: '서울에 많다',
        ),
      );
      final next = applyGuess(
        puzzle: withHint,
        guess: '지하천역',
        result: const GuessResult(
          isCorrect: false,
          attemptsLeft: 1,
          feedback: [true, false, false, true],
        ),
      );

      expect(next.hint, '서울에 많다');
      expect(next.attempts, hasLength(2));
    });
  });

  group('timeUntilNextPuzzle', () {
    // 퍼즐은 KST 자정에 바뀐다(ADR 0001). 기기 시간대와 무관하게 같은 값이어야 한다.
    test('KST 자정까지 남은 시간을 돌려준다', () {
      // 2026-10-13 16:47:27 KST = 07:47:27 UTC
      final now = DateTime.utc(2026, 10, 13, 7, 47, 27);

      expect(
        timeUntilNextPuzzle(now),
        const Duration(hours: 7, minutes: 12, seconds: 33),
      );
    });

    test('기기가 어느 시간대에 있어도 같은 값이다', () {
      final utc = DateTime.utc(2026, 10, 13, 7, 47, 27);

      expect(timeUntilNextPuzzle(utc.toLocal()), timeUntilNextPuzzle(utc));
    });

    test('KST 자정 직후에는 24시간 가까이 남는다', () {
      // 2026-10-13 00:00:01 KST
      final now = DateTime.utc(2026, 10, 12, 15, 0, 1);

      expect(
        timeUntilNextPuzzle(now),
        const Duration(hours: 23, minutes: 59, seconds: 59),
      );
    });
  });

  group('formatCountdown', () {
    test('시:분:초 두 자리로 찍는다', () {
      expect(
        formatCountdown(const Duration(hours: 7, minutes: 12, seconds: 33)),
        '07:12:33',
      );
      expect(formatCountdown(Duration.zero), '00:00:00');
      expect(formatCountdown(const Duration(seconds: -5)), '00:00:00');
    });
  });
}
