import 'dart:convert';

import 'package:chosung/api/api_models.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';

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
          "linked_account": {"provider": "google", "email": "a***@b.com"},
          "entitlement": {
            "active": true,
            "until": "2026-11-01T00:00:00Z",
            "status": "active",
            "source": "apple",
            "next_check_at": "2026-10-15T13:00:00Z"
          }
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
      expect(stats.entitlement.active, isTrue);
      // 앱은 이 시각에 타이머를 걸고 다시 부른다(스펙 §A.8). 기기 로컬시로
      // 읽으면 몇 시간씩 틀어지므로 UTC 로 남아 있어야 한다.
      expect(stats.entitlement.nextCheckAt, DateTime.utc(2026, 10, 15, 13));
      expect(stats.entitlement.nextCheckAt!.isUtc, isTrue);
    });

    test('게스트(미연결)는 linked_account 가 null 이다', () {
      final stats = MyStats.fromJson(
        jsonDecode('''
        {
          "puzzle_language": "ko",
          "current_streak": 0,
          "max_streak": 0,
          "solved_count": 0,
          "linked_account": null,
          "entitlement": {
            "active": false,
            "until": null,
            "status": null,
            "source": null,
            "next_check_at": null
          }
        }
        ''')
            as Map<String, dynamic>,
      );

      expect(stats.puzzleLanguage, PuzzleLanguage.ko);
      expect(stats.linkedAccount, isNull);
      expect(stats.entitlement.active, isFalse);
      // 구독 행이 없으면 다시 물어볼 것도 없다 — 재확인 타이머가 안 걸린다.
      expect(stats.entitlement.nextCheckAt, isNull);
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

  group('TodayStats.fromJson', () {
    test('by_attempt 는 시도 횟수를 키로 가진 비율 표가 된다', () {
      final stats = TodayStats.fromJson(
        jsonDecode(
              '{"date": "2026-10-13", "language": "ko", "total_solved": 100, '
              '"by_attempt": {"1": 0.08, "2": 0.31, "3": 0.4, "4": 0.15, '
              '"5": 0.06}}',
            )
            as Map<String, dynamic>,
      );

      expect(stats.date, DateTime(2026, 10, 13));
      expect(stats.language, PuzzleLanguage.ko);
      expect(stats.totalSolved, 100);
      expect(stats.byAttempt, {1: 0.08, 2: 0.31, 3: 0.4, 4: 0.15, 5: 0.06});
    });

    // 아직 아무도 못 푼 퍼즐은 서버가 전부 0.0 을 보낸다(정수 0 으로 올 수도 있다).
    test('정수로 온 비율도 double 로 읽는다', () {
      final stats = TodayStats.fromJson(
        jsonDecode(
              '{"date": "2026-10-13", "language": "en", "total_solved": 0, '
              '"by_attempt": {"1": 0, "2": 0}}',
            )
            as Map<String, dynamic>,
      );

      expect(stats.totalSolved, 0);
      expect(stats.byAttempt, {1: 0.0, 2: 0.0});
    });

    // 서버가 앱보다 먼저 칸을 늘려도(또는 모르는 키를 보내도) 떠야 한다.
    test('숫자가 아닌 키는 버린다', () {
      final stats = TodayStats.fromJson(
        jsonDecode(
              '{"date": "2026-10-13", "language": "ko", "total_solved": 1, '
              '"by_attempt": {"1": 1.0, "fail": 0.0}}',
            )
            as Map<String, dynamic>,
      );

      expect(stats.byAttempt, {1: 1.0});
    });
  });

  group('TodayStats.isFor', () {
    TodayStats statsOf(DateTime date, PuzzleLanguage language) => TodayStats(
      date: date,
      language: language,
      totalSolved: 1,
      byAttempt: const {1: 1.0},
    );

    test('같은 날짜·언어면 그 퍼즐의 집계다', () {
      final puzzle = fakeTodayPuzzle(date: DateTime(2026, 10, 13));

      expect(
        statsOf(DateTime(2026, 10, 13), PuzzleLanguage.ko).isFor(puzzle),
        isTrue,
      );
    });

    // 결과 시트를 열어 둔 채 KST 자정을 넘기면 재조회가 다음 날 집계를 받는다.
    test('날짜가 하루라도 다르면 아니다(D-26-1)', () {
      final puzzle = fakeTodayPuzzle(date: DateTime(2026, 10, 13));

      expect(
        statsOf(DateTime(2026, 10, 14), PuzzleLanguage.ko).isFor(puzzle),
        isFalse,
      );
      expect(
        statsOf(DateTime(2026, 10, 12), PuzzleLanguage.ko).isFor(puzzle),
        isFalse,
      );
    });

    test('언어가 다르면 아니다(D-26-1)', () {
      // 가짜 퍼즐의 기본 언어는 ko 다.
      final puzzle = fakeTodayPuzzle(date: DateTime(2026, 10, 13));

      expect(
        statsOf(DateTime(2026, 10, 13), PuzzleLanguage.en).isFor(puzzle),
        isFalse,
      );
    });

    // 서버는 `YYYY-MM-DD` 만 보내지만, 시각이 섞여 와도 날짜로만 본다.
    test('시각이 붙어 와도 날짜만 본다', () {
      final puzzle = fakeTodayPuzzle(date: DateTime(2026, 10, 13));

      expect(
        statsOf(
          DateTime(2026, 10, 13, 23, 59),
          PuzzleLanguage.ko,
        ).isFor(puzzle),
        isTrue,
      );
    });
  });

  group('Leaderboard.fromJson', () {
    test('서버 응답(/api/v1/puzzles/today/leaderboard)을 그대로 읽는다', () {
      final board = Leaderboard.fromJson(
        jsonDecode('''
        {
          "date": "2026-10-13",
          "language": "ko",
          "entries": [
            {"rank": 1, "anon_tag": "a3f1", "attempts": 1,
             "seconds": 41, "is_me": false},
            {"rank": 2, "anon_tag": "7b20", "attempts": 2,
             "seconds": 221, "is_me": true}
          ],
          "me": {"rank": 2, "attempts": 2, "seconds": 221}
        }
        ''')
            as Map<String, dynamic>,
      );

      expect(board.date, DateTime(2026, 10, 13));
      expect(board.language, PuzzleLanguage.ko);
      expect(board.entries.first.rank, 1);
      expect(board.entries.first.anonTag, 'a3f1');
      expect(board.entries.first.attempts, 1);
      expect(board.entries.first.seconds, 41);
      expect(board.entries.first.isMe, isFalse);
      expect(board.entries.last.isMe, isTrue);
      expect(board.me?.rank, 2);
      expect(board.me?.attempts, 2);
      expect(board.me?.seconds, 221);
    });

    test('아직 아무도 못 풀었으면 entries 는 비고 me 는 null 이다', () {
      final board = Leaderboard.fromJson(
        jsonDecode('''
        {"date": "2026-10-13", "language": "en", "entries": [], "me": null}
        ''')
            as Map<String, dynamic>,
      );

      expect(board.entries, isEmpty);
      expect(board.me, isNull);
      expect(board.language, PuzzleLanguage.en);
    });
  });

  group('HistoryDay.fromJson', () {
    test('하루의 언어별 결과를 읽는다', () {
      final day = HistoryDay.fromJson(
        jsonDecode('''
        {"date": "2026-10-12", "results": {"ko": "success", "en": "none"}}
        ''')
            as Map<String, dynamic>,
      );

      expect(day.date, DateTime(2026, 10, 12));
      expect(day.results[PuzzleLanguage.ko], DayResult.success);
      expect(day.results[PuzzleLanguage.en], DayResult.none);
    });

    test('서버가 먼저 늘린 언어·결과는 버리거나 미플레이로 떨어뜨린다', () {
      final day = HistoryDay.fromJson(
        jsonDecode('''
        {"date": "2026-10-12",
         "results": {"ko": "surrendered", "en": "in_progress", "ja": "fail"}}
        ''')
            as Map<String, dynamic>,
      );

      // 모르는 언어는 그릴 칸이 없고, 모르는 결과는 색칠하지 않는다.
      expect(day.results.keys, [PuzzleLanguage.ko, PuzzleLanguage.en]);
      expect(day.results[PuzzleLanguage.ko], DayResult.none);
      expect(day.results[PuzzleLanguage.en], DayResult.inProgress);
    });
  });

  group('Entitlement.fromJson', () {
    test('권한과 근거를 읽고, 시각은 UTC 로 받는다', () {
      final entitlement = Entitlement.fromJson(
        jsonDecode('''
        {"active": true,
         "until": "2026-11-01T00:00:00+00:00",
         "status": "active",
         "source": "apple",
         "next_check_at": "2026-10-15T04:00:00+00:00"}
        ''')
            as Map<String, dynamic>,
      );

      expect(entitlement.active, isTrue);
      // 서버가 타임존을 붙여 보내므로(`EntitlementResponse` docstring) 기기
      // 로컬시로 오해하지 않는다 — 몇 시간씩 틀어지는 지점이다.
      expect(entitlement.until, DateTime.utc(2026, 11));
      expect(entitlement.until!.isUtc, isTrue);
      expect(entitlement.status, SubscriptionStatus.active);
      expect(entitlement.source, SubscriptionStore.apple);
      expect(entitlement.nextCheckAt, DateTime.utc(2026, 10, 15, 4));
    });

    test('구독이 없으면 active 만 false 고 나머지는 null 이다', () {
      final entitlement = Entitlement.fromJson(
        jsonDecode('''
        {"active": false, "until": null, "status": null,
         "source": null, "next_check_at": null}
        ''')
            as Map<String, dynamic>,
      );

      expect(entitlement.active, isFalse);
      expect(entitlement.until, isNull);
      expect(entitlement.status, isNull);
      expect(entitlement.source, isNull);
      expect(entitlement.nextCheckAt, isNull);
    });

    test('서버가 먼저 늘린 상태·스토어는 null 로 떨어뜨린다', () {
      // 권한(`active`)은 서버가 판정해서 보내므로 모르는 라벨이 와도 광고를
      // 끄는 판단은 흔들리지 않는다. 라벨만 모르는 것으로 둔다.
      final entitlement = Entitlement.fromJson(
        jsonDecode('''
        {"active": true, "until": null, "status": "paused",
         "source": "amazon", "next_check_at": null}
        ''')
            as Map<String, dynamic>,
      );

      expect(entitlement.active, isTrue);
      expect(entitlement.status, isNull);
      expect(entitlement.source, isNull);
    });
  });
}
