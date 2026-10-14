import 'dart:convert';

import 'package:chosung/api/api_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AppConfig.fromJson', () {
    test('서버 응답(/api/v1/config)을 그대로 읽는다', () {
      final config = AppConfig.fromJson(
        jsonDecode('''
        {
          "min_app_version": {"ios": "1.0.0", "android": "1.0.1"},
          "maintenance": {"enabled": true, "message": "오전 3시까지"},
          "languages": ["ko", "en"],
          "store_urls": {"ios": "https://apps.apple.com/app/id1", "android": null}
        }
        ''')
            as Map<String, dynamic>,
      );

      expect(config.minAppVersion.ios, '1.0.0');
      expect(config.minAppVersion.android, '1.0.1');
      expect(config.maintenance.enabled, isTrue);
      expect(config.maintenance.message, '오전 3시까지');
      expect(config.languages, [PuzzleLanguage.ko, PuzzleLanguage.en]);
      expect(config.storeUrls.ios, 'https://apps.apple.com/app/id1');
      expect(config.storeUrls.android, isNull);
    });

    test('스토어 등록 전 null 과 점검 메시지 없음을 받아낸다', () {
      final config = AppConfig.fromJson(
        jsonDecode('''
        {
          "min_app_version": {"ios": "1.0.0", "android": "1.0.0"},
          "maintenance": {"enabled": false, "message": null},
          "languages": ["ko", "en"],
          "store_urls": {"ios": null, "android": null}
        }
        ''')
            as Map<String, dynamic>,
      );

      expect(config.maintenance.enabled, isFalse);
      expect(config.maintenance.message, isNull);
      expect(config.storeUrls.ios, isNull);
    });

    // 서버가 앱보다 먼저 언어를 늘려도 앱이 떠야 한다.
    test('모르는 언어 코드는 건너뛴다', () {
      final config = AppConfig.fromJson(
        jsonDecode('''
        {
          "min_app_version": {"ios": "1.0.0", "android": "1.0.0"},
          "maintenance": {"enabled": false, "message": null},
          "languages": ["ko", "ja", "en"],
          "store_urls": {"ios": null, "android": null}
        }
        ''')
            as Map<String, dynamic>,
      );

      expect(config.languages, [PuzzleLanguage.ko, PuzzleLanguage.en]);
    });
  });

  group('MyStats.fromJson', () {
    test('연결된 계정이 있는 응답을 읽는다', () {
      final stats = MyStats.fromJson(
        jsonDecode('''
        {
          "puzzle_language": "en",
          "current_streak": 3,
          "max_streak": 12,
          "solved_count": 41,
          "linked_account": {"provider": "google", "email": "a***@b.com"}
        }
        ''')
            as Map<String, dynamic>,
      );

      expect(stats.puzzleLanguage, PuzzleLanguage.en);
      expect(stats.currentStreak, 3);
      expect(stats.maxStreak, 12);
      expect(stats.solvedCount, 41);
      expect(stats.linkedAccount?.provider, 'google');
      expect(stats.linkedAccount?.email, 'a***@b.com');
    });

    test('게스트(미연결)는 linked_account 가 null 이다', () {
      final stats = MyStats.fromJson(
        jsonDecode('''
        {
          "puzzle_language": "ko",
          "current_streak": 0,
          "max_streak": 0,
          "solved_count": 0,
          "linked_account": null
        }
        ''')
            as Map<String, dynamic>,
      );

      expect(stats.puzzleLanguage, PuzzleLanguage.ko);
      expect(stats.linkedAccount, isNull);
    });
  });

  group('PuzzleLanguage', () {
    test('wire 값으로 왕복한다', () {
      expect(PuzzleLanguage.fromWire('ko'), PuzzleLanguage.ko);
      expect(PuzzleLanguage.fromWire('en'), PuzzleLanguage.en);
      expect(PuzzleLanguage.fromWire('ja'), isNull);
      expect(PuzzleLanguage.ko.wire, 'ko');
    });

    test('기기 언어가 영어면 en, 나머지는 ko 로 시작한다', () {
      expect(PuzzleLanguage.forDeviceLanguage('en'), PuzzleLanguage.en);
      expect(PuzzleLanguage.forDeviceLanguage('ko'), PuzzleLanguage.ko);
      expect(PuzzleLanguage.forDeviceLanguage('ja'), PuzzleLanguage.ko);
    });
  });

  group('TodayPuzzle.fromJson', () {
    test('ko 퍼즐 응답을 그대로 읽는다', () {
      final puzzle = TodayPuzzle.fromJson(
        jsonDecode('''
        {
          "puzzle_id": 42,
          "date": "2026-10-13",
          "language": "ko",
          "mask": [
            {"t": "r", "c": "\u3148"},
            {"t": "r", "c": "\u314e"},
            {"t": "h", "c": ""}
          ],
          "chosung": "\u3148\u314e_",
          "length": 3,
          "category": "general",
          "attempts_left": 4,
          "attempts": [
            {"guess": "\uc9c0\ud558\ucabd", "feedback": [true, true, false]}
          ],
          "status": "in_progress",
          "hint_unlocked": false,
          "hint": null,
          "answer": null
        }
        ''')
            as Map<String, dynamic>,
      );

      expect(puzzle.puzzleId, 42);
      expect(puzzle.date, DateTime(2026, 10, 13));
      expect(puzzle.language, PuzzleLanguage.ko);
      expect(puzzle.length, 3);
      expect(puzzle.category, WordCategory.general);
      expect(puzzle.attemptsLeft, 4);
      expect(puzzle.status, PuzzleStatus.inProgress);
      expect(puzzle.hintUnlocked, isFalse);
      expect(puzzle.hint, isNull);
      expect(puzzle.answer, isNull);
      expect(puzzle.mask.map((tile) => tile.type), [
        MaskTileType.revealed,
        MaskTileType.revealed,
        MaskTileType.hidden,
      ]);
      expect(puzzle.mask.first.char, '\u3148');
      expect(puzzle.attempts.single.guess, '\uc9c0\ud558\ucabd');
      expect(puzzle.attempts.single.feedback, [true, true, false]);
    });

    test('en 퍼즐의 구분자 타일(`s`)과 끝난 퍼즐의 정답을 읽는다', () {
      final puzzle = TodayPuzzle.fromJson(
        jsonDecode('''
        {
          "puzzle_id": 7,
          "date": "2026-10-14",
          "language": "en",
          "mask": [
            {"t": "r", "c": "H"},
            {"t": "s", "c": " "},
            {"t": "h", "c": ""}
          ],
          "chosung": "H _",
          "length": 2,
          "category": "book_title",
          "attempts_left": 0,
          "attempts": [
            {"guess": "HO", "feedback": [true, true]}
          ],
          "status": "success",
          "hint_unlocked": true,
          "hint": "\ucc45 \uc81c\ubaa9",
          "answer": "H O"
        }
        ''')
            as Map<String, dynamic>,
      );

      expect(puzzle.category, WordCategory.bookTitle);
      expect(puzzle.status, PuzzleStatus.success);
      expect(puzzle.status.isFinished, isTrue);
      expect(puzzle.mask[1].type, MaskTileType.separator);
      // 구분자는 글자 수에 안 들어간다 — 타일 3개짜리 mask 의 length 는 2다.
      expect(puzzle.length, 2);
      expect(puzzle.separatorCount, 1);
      expect(puzzle.hintUnlocked, isTrue);
      expect(puzzle.answer, 'H O');
    });

    // 서버가 앱보다 먼저 타일 종류·카테고리를 늘릴 수 있다. 모르는 타일을 글자로
    // 그리면 정답이 새어나갈 수 있으므로 빈 타일로 떨어뜨린다.
    test('모르는 타일 종류는 빈 타일, 모르는 카테고리는 일반 단어로 읽는다', () {
      final puzzle = TodayPuzzle.fromJson(
        jsonDecode('''
        {
          "puzzle_id": 1,
          "date": "2026-10-13",
          "language": "ko",
          "mask": [{"t": "x", "c": "\uc9c0"}],
          "chosung": "_",
          "length": 1,
          "category": "poem",
          "attempts_left": 5,
          "attempts": [],
          "status": "in_progress",
          "hint_unlocked": false
        }
        ''')
            as Map<String, dynamic>,
      );

      expect(puzzle.mask.single.type, MaskTileType.hidden);
      expect(puzzle.category, WordCategory.general);
      expect(puzzle.attempts, isEmpty);
    });
  });

  group('GuessResult.fromJson', () {
    test('오답은 글자별 피드백이 온다', () {
      final result = GuessResult.fromJson(
        jsonDecode(
              '{"is_correct": false, "feedback": [true, false], '
              '"attempts_left": 3, "hint": null, "answer": null}',
            )
            as Map<String, dynamic>,
      );

      expect(result.isCorrect, isFalse);
      expect(result.feedback, [true, false]);
      expect(result.attemptsLeft, 3);
    });

    // 정답이면 서버는 feedback 을 null 로 준다(README "04. 시도 이력…").
    test('정답은 feedback 이 null 이고 정답 문자열이 온다', () {
      final result = GuessResult.fromJson(
        jsonDecode(
              '{"is_correct": true, "feedback": null, "attempts_left": 3, '
              '"hint": null, "answer": "\uc9c0\ud558\ucca0\uc5ed"}',
            )
            as Map<String, dynamic>,
      );

      expect(result.isCorrect, isTrue);
      expect(result.feedback, isNull);
      expect(result.answer, '\uc9c0\ud558\ucca0\uc5ed');
    });
  });
}
