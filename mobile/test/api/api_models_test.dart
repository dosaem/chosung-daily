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
}
