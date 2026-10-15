import 'dart:convert';
import 'dart:typed_data';

import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/dio_api_client.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

/// 네트워크를 타지 않고 Dio 의 요청을 받아 정해진 응답을 돌려준다.
/// provider 경계 한 곳만 가짜로 두는 이 레포 규칙과 같은 방식.
class _RecordingAdapter implements HttpClientAdapter {
  _RecordingAdapter(this.respond);

  final ResponseBody Function(RequestOptions options) respond;
  final List<RequestOptions> requests = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return respond(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _json(Map<String, dynamic> body, int statusCode) =>
    ResponseBody.fromString(
      jsonEncode(body),
      statusCode,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );

DioApiClient _clientWith(
  _RecordingAdapter adapter, {
  String? token,
}) {
  final dio = Dio(BaseOptions(baseUrl: 'https://example.test/api/v1'))
    ..httpClientAdapter = adapter;
  return DioApiClient(dio: dio, readToken: () => token);
}

void main() {
  test('POST /guests 는 퍼즐 언어를 보내고 토큰을 돌려준다', () async {
    final adapter = _RecordingAdapter(
      (_) => _json({'token': 'guest-token'}, 201),
    );
    final client = _clientWith(adapter);

    final token = await client.createGuest(puzzleLanguage: PuzzleLanguage.en);

    expect(token, 'guest-token');
    expect(adapter.requests.single.path, '/guests');
    expect(adapter.requests.single.method, 'POST');
    expect(adapter.requests.single.data, {'puzzle_language': 'en'});
    // 인증이 없는 엔드포인트다 — 토큰이 없어도 호출된다.
    expect(
      adapter.requests.single.headers.containsKey('Authorization'),
      isFalse,
    );
  });

  test('GET /config 는 Bearer 없이 호출한다', () async {
    final adapter = _RecordingAdapter(
      (_) => _json({
        'min_app_version': {'ios': '1.0.0', 'android': '1.0.0'},
        'maintenance': {'enabled': false, 'message': null},
        'languages': ['ko', 'en'],
        'store_urls': {'ios': null, 'android': null},
      }, 200),
    );
    final client = _clientWith(adapter, token: 'guest-token');

    final config = await client.fetchConfig();

    expect(config.minAppVersion.ios, '1.0.0');
    expect(adapter.requests.single.path, '/config');
    expect(
      adapter.requests.single.headers.containsKey('Authorization'),
      isFalse,
    );
  });

  test('GET /me/stats 는 현재 게스트 토큰을 Bearer 로 붙인다', () async {
    final adapter = _RecordingAdapter(
      (_) => _json({
        'puzzle_language': 'ko',
        'current_streak': 1,
        'max_streak': 2,
        'solved_count': 3,
        'linked_account': null,
      }, 200),
    );
    final client = _clientWith(adapter, token: 'guest-token');

    final stats = await client.fetchMyStats();

    expect(stats.currentStreak, 1);
    expect(
      adapter.requests.single.headers['Authorization'],
      'Bearer guest-token',
    );
  });

  // 27 이 토큰을 교체하면 같은 Dio 인스턴스가 다음 요청부터 새 토큰을 써야
  // 한다 — 헤더를 생성 시점에 한 번 굽지 않는다는 뜻이다.
  test('같은 클라이언트가 요청마다 토큰을 다시 읽는다', () async {
    final adapter = _RecordingAdapter(
      (_) => _json({
        'puzzle_language': 'ko',
        'current_streak': 1,
        'max_streak': 2,
        'solved_count': 3,
        'linked_account': null,
      }, 200),
    );
    var token = 'first-token';
    final dio = Dio(BaseOptions(baseUrl: 'https://example.test/api/v1'))
      ..httpClientAdapter = adapter;
    final client = DioApiClient(dio: dio, readToken: () => token);

    await client.fetchMyStats();
    token = 'second-token';
    await client.fetchMyStats();

    expect(
      adapter.requests.map((r) => r.headers['Authorization']).toList(),
      ['Bearer first-token', 'Bearer second-token'],
    );
  });

  test('토큰이 없는데 Bearer 가 필요한 호출은 네트워크를 타지 않는다', () async {
    final adapter = _RecordingAdapter((_) => _json(const {}, 200));
    final client = _clientWith(adapter);

    await expectLater(
      client.fetchMyStats(),
      throwsA(isA<UnauthorizedApiException>()),
    );
    expect(adapter.requests, isEmpty);
  });

  group('에러 매핑', () {
    test('401 은 UnauthorizedApiException', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({'code': 'UNAUTHORIZED', 'message': '인증이 필요합니다.'}, 401),
      );
      final client = _clientWith(adapter, token: 'stale');

      await expectLater(
        client.fetchMyStats(),
        throwsA(
          isA<UnauthorizedApiException>()
              .having((e) => e.code, 'code', 'UNAUTHORIZED')
              .having((e) => e.message, 'message', '인증이 필요합니다.'),
        ),
      );
    });

    test('400 VALIDATION_ERROR 는 ValidationApiException', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({
          'code': 'VALIDATION_ERROR',
          'message': '요청 값이 올바르지 않습니다.',
        }, 400),
      );
      final client = _clientWith(adapter);

      await expectLater(
        client.createGuest(puzzleLanguage: PuzzleLanguage.ko),
        throwsA(isA<ValidationApiException>()),
      );
    });

    test('5xx 는 ServerApiException', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({'code': 'INTERNAL_ERROR', 'message': '서버 오류'}, 500),
      );
      final client = _clientWith(adapter);

      await expectLater(
        client.fetchConfig(),
        throwsA(isA<ServerApiException>()),
      );
    });

    test('연결 실패는 NetworkApiException', () async {
      final adapter = _RecordingAdapter((options) {
        throw DioException.connectionError(
          requestOptions: options,
          reason: 'offline',
        );
      });
      final client = _clientWith(adapter);

      await expectLater(
        client.fetchConfig(),
        throwsA(isA<NetworkApiException>()),
      );
    });

    test('본문이 {code,message} 가 아니어도 상태 코드로 매핑한다', () async {
      final adapter = _RecordingAdapter(
        (_) => ResponseBody.fromString('<html>502</html>', 502),
      );
      final client = _clientWith(adapter);

      await expectLater(
        client.fetchConfig(),
        throwsA(
          isA<ServerApiException>().having(
            (e) => e.code,
            'code',
            'UNKNOWN_ERROR',
          ),
        ),
      );
    });
  });

  group('퍼즐 엔드포인트', () {
    Map<String, dynamic> todayBody() => {
      'puzzle_id': 42,
      'date': '2026-10-13',
      'language': 'ko',
      'mask': [
        {'t': 'r', 'c': 'ㅈ'},
        {'t': 'h', 'c': ''},
      ],
      'chosung': 'ㅈ_',
      'length': 2,
      'category': 'general',
      'attempts_left': 5,
      'attempts': <Map<String, dynamic>>[],
      'status': 'in_progress',
      'hint_unlocked': false,
      'hint': null,
      'answer': null,
    };

    test('GET /puzzles/today 는 Bearer 로 호출하고 보드를 읽어온다', () async {
      final adapter = _RecordingAdapter((_) => _json(todayBody(), 200));
      final client = _clientWith(adapter, token: 'guest-token');

      final puzzle = await client.fetchTodayPuzzle();

      expect(puzzle.puzzleId, 42);
      expect(puzzle.length, 2);
      expect(adapter.requests.single.path, '/puzzles/today');
      expect(adapter.requests.single.method, 'GET');
      expect(
        adapter.requests.single.headers['Authorization'],
        'Bearer guest-token',
      );
    });

    test('퍼즐이 아직 없으면 NoPuzzleTodayApiException', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({
          'code': 'NO_PUZZLE_TODAY',
          'message': '오늘의 퍼즐이 아직 준비되지 않았습니다.',
        }, 404),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      await expectLater(
        client.fetchTodayPuzzle(),
        throwsA(isA<NoPuzzleTodayApiException>()),
      );
    });

    test('POST /puzzles/today/guesses 는 puzzle_id 를 같이 보낸다', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({
          'is_correct': false,
          'feedback': [true, false],
          'attempts_left': 4,
          'hint': null,
          'answer': null,
        }, 200),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      final result = await client.submitGuess(puzzleId: 42, guess: '지하');

      expect(result.isCorrect, isFalse);
      expect(result.feedback, [true, false]);
      expect(result.attemptsLeft, 4);
      expect(adapter.requests.single.path, '/puzzles/today/guesses');
      expect(adapter.requests.single.method, 'POST');
      expect(adapter.requests.single.data, {
        'puzzle_id': 42,
        'guess': '지하',
      });
      expect(
        adapter.requests.single.headers['Authorization'],
        'Bearer guest-token',
      );
    });

    // 자정 경과·다른 기기에서 언어 변경. 시도는 소비되지 않았고 할 일은 새로고침뿐이다.
    test('409 PUZZLE_CHANGED 는 전용 예외로 온다', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({
          'code': 'PUZZLE_CHANGED',
          'message': '퍼즐이 바뀌었어요. 새로고침해주세요.',
        }, 409),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      await expectLater(
        client.submitGuess(puzzleId: 41, guess: '지하'),
        throwsA(isA<PuzzleChangedApiException>()),
      );
    });

    // 티켓 31 보상형 힌트 미리 보기. 시도를 소비하지 않는 별도 엔드포인트다.
    test('POST /puzzles/today/hint-unlock 은 puzzle_id 를 보내고 힌트를 받는다', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({'hint': '서울에 가장 많다'}, 200),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      final hint = await client.unlockHint(puzzleId: 41);

      expect(hint, '서울에 가장 많다');
      expect(adapter.requests.single.path, '/puzzles/today/hint-unlock');
      expect(adapter.requests.single.method, 'POST');
      expect(adapter.requests.single.data, {'puzzle_id': 41});
      expect(
        adapter.requests.single.headers['Authorization'],
        'Bearer guest-token',
      );
    });

    test('409 HINT_ALREADY_UNLOCKED 는 전용 예외로 온다', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({
          'code': 'HINT_ALREADY_UNLOCKED',
          'message': '이미 힌트를 열었어요.',
        }, 409),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      await expectLater(
        client.unlockHint(puzzleId: 41),
        throwsA(isA<HintAlreadyUnlockedApiException>()),
      );
    });

    test('409 ALREADY_FINISHED 는 전용 예외로 온다', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({
          'code': 'ALREADY_FINISHED',
          'message': '이미 끝난 퍼즐이에요.',
        }, 409),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      await expectLater(
        client.unlockHint(puzzleId: 41),
        throwsA(isA<AlreadyFinishedApiException>()),
      );
    });

    test('PATCH /me 는 바뀐 퍼즐 언어를 돌려준다', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({'puzzle_language': 'en'}, 200),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      final language = await client.updatePuzzleLanguage(PuzzleLanguage.en);

      expect(language, PuzzleLanguage.en);
      expect(adapter.requests.single.path, '/me');
      expect(adapter.requests.single.method, 'PATCH');
      expect(adapter.requests.single.data, {'puzzle_language': 'en'});
      expect(
        adapter.requests.single.headers['Authorization'],
        'Bearer guest-token',
      );
    });

    test('토큰이 없으면 서버까지 가지 않고 401 과 같은 예외를 낸다', () async {
      final adapter = _RecordingAdapter((_) => _json(todayBody(), 200));
      final client = _clientWith(adapter);

      await expectLater(
        client.fetchTodayPuzzle(),
        throwsA(isA<UnauthorizedApiException>()),
      );
      expect(adapter.requests, isEmpty);
    });

    test('GET /puzzles/today/stats 는 Bearer 를 달고 분포를 돌려준다', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({
          'date': '2026-10-13',
          'language': 'ko',
          'total_solved': 100,
          'by_attempt': {'1': 0.08, '2': 0.31, '3': 0.4, '4': 0.15, '5': 0.06},
        }, 200),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      final stats = await client.fetchTodayStats(language: PuzzleLanguage.en);

      expect(stats.totalSolved, 100);
      expect(stats.byAttempt[3], 0.4);
      expect(adapter.requests.single.path, '/puzzles/today/stats');
      expect(adapter.requests.single.method, 'GET');
      expect(
        adapter.requests.single.headers['Authorization'],
        'Bearer guest-token',
      );
      // 언어를 반드시 보낸다(D-26-1) — 빼면 서버가 요청 시점의 게스트 선호
      // 언어로 집계를 골라서 내가 푼 퍼즐과 다른 분포가 온다.
      expect(adapter.requests.single.queryParameters, {'language': 'en'});
    });

    test('아직 퍼즐이 없으면 stats 도 전용 예외로 온다', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({
          'code': 'NO_PUZZLE_TODAY',
          'message': '아직 준비되지 않았습니다.',
        }, 404),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      await expectLater(
        client.fetchTodayStats(language: PuzzleLanguage.ko),
        throwsA(isA<NoPuzzleTodayApiException>()),
      );
    });
  });

  group('순위·기록 엔드포인트', () {
    test('GET /puzzles/today/leaderboard 는 limit 을 붙여 Bearer 로 부른다', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({
          'date': '2026-10-13',
          'language': 'ko',
          'entries': [
            {
              'rank': 1,
              'anon_tag': 'a3f1',
              'attempts': 1,
              'seconds': 41,
              'is_me': true,
            },
          ],
          'me': {'rank': 1, 'attempts': 1, 'seconds': 41},
        }, 200),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      final board = await client.fetchTodayLeaderboard();

      expect(board.entries.single.anonTag, 'a3f1');
      expect(board.me?.rank, 1);
      expect(adapter.requests.single.path, '/puzzles/today/leaderboard');
      expect(adapter.requests.single.method, 'GET');
      // 언어는 보내지 않는다 — 서버가 게스트 선호 언어로 고른다(S3 칩은 표시 전용).
      expect(adapter.requests.single.queryParameters, {'limit': 20});
      expect(
        adapter.requests.single.headers['Authorization'],
        'Bearer guest-token',
      );
    });

    test('그 언어의 오늘 퍼즐이 없으면 NoPuzzleTodayApiException', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({
          'code': 'NO_PUZZLE_TODAY',
          'message': '오늘 퍼즐이 아직 없습니다.',
        }, 404),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      await expectLater(
        client.fetchTodayLeaderboard(),
        throwsA(isA<NoPuzzleTodayApiException>()),
      );
    });

    test('GET /me/history 는 days 를 붙이고 날짜 목록을 돌려준다', () async {
      final adapter = _RecordingAdapter(
        (_) => ResponseBody.fromString(
          jsonEncode([
            {
              'date': '2026-10-12',
              'results': {'ko': 'success', 'en': 'none'},
            },
            {
              'date': '2026-10-13',
              'results': {'ko': 'in_progress', 'en': 'fail'},
            },
          ]),
          200,
          headers: {
            Headers.contentTypeHeader: [Headers.jsonContentType],
          },
        ),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      final history = await client.fetchMyHistory();

      expect(history.length, 2);
      expect(history.first.date, DateTime(2026, 10, 12));
      expect(history.first.results[PuzzleLanguage.ko], DayResult.success);
      expect(history.last.results[PuzzleLanguage.en], DayResult.fail);
      expect(adapter.requests.single.path, '/me/history');
      expect(adapter.requests.single.queryParameters, {'days': 7});
      expect(
        adapter.requests.single.headers['Authorization'],
        'Bearer guest-token',
      );
    });

    test('토큰이 없으면 두 호출 다 서버까지 가지 않는다', () async {
      final adapter = _RecordingAdapter((_) => _json(const {}, 200));
      final client = _clientWith(adapter);

      await expectLater(
        client.fetchTodayLeaderboard(),
        throwsA(isA<UnauthorizedApiException>()),
      );
      await expectLater(
        client.fetchMyHistory(),
        throwsA(isA<UnauthorizedApiException>()),
      );
      expect(adapter.requests, isEmpty);
    });
  });

  group('계정 연결·전환·삭제 (티켓 29)', () {
    test(
      'POST /auth/token-exchange 는 provider·id_token 을 Bearer 와 함께 보낸다',
      () async {
        final adapter = _RecordingAdapter(
          (_) => _json({'token': 'linked-token'}, 200),
        );
        final client = _clientWith(adapter, token: 'guest-token');

        final token = await client.exchangeIdToken(
          provider: 'google',
          idToken: 'id-token',
        );

        expect(token, 'linked-token');
        expect(adapter.requests.single.path, '/auth/token-exchange');
        expect(adapter.requests.single.method, 'POST');
        // 구글은 authorization_code 가 없다 — 키 자체를 보내지 않는다.
        expect(adapter.requests.single.data, {
          'provider': 'google',
          'id_token': 'id-token',
        });
        expect(
          adapter.requests.single.headers['Authorization'],
          'Bearer guest-token',
        );
      },
    );

    test('애플은 authorization_code 를 같이 보낸다', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({'token': 'linked-token'}, 200),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      await client.exchangeIdToken(
        provider: 'apple',
        idToken: 'id-token',
        authorizationCode: 'auth-code',
      );

      expect(adapter.requests.single.data, {
        'provider': 'apple',
        'id_token': 'id-token',
        'authorization_code': 'auth-code',
      });
    });

    test(
      '401 INVALID_ID_TOKEN 과 409 ACCOUNT_ALREADY_LINKED 는 각각의 예외다',
      () async {
        final invalid = _RecordingAdapter(
          (_) => _json({
            'code': 'INVALID_ID_TOKEN',
            'message': 'id_token 검증에 실패했습니다.',
          }, 401),
        );
        final linked = _RecordingAdapter(
          (_) => _json({
            'code': 'ACCOUNT_ALREADY_LINKED',
            'message': '이미 다른 계정이 연결돼 있습니다.',
          }, 409),
        );

        await expectLater(
          _clientWith(
            invalid,
            token: 'guest-token',
          ).exchangeIdToken(provider: 'google', idToken: 'bad'),
          throwsA(isA<InvalidIdTokenApiException>()),
        );
        await expectLater(
          _clientWith(
            linked,
            token: 'guest-token',
          ).exchangeIdToken(provider: 'google', idToken: 'ok'),
          throwsA(isA<AccountAlreadyLinkedApiException>()),
        );
      },
    );

    test('DELETE /me 는 본문 없는 204 를 그대로 받는다', () async {
      final adapter = _RecordingAdapter(
        (_) => ResponseBody.fromString('', 204),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      await client.deleteAccount();

      expect(adapter.requests.single.path, '/me');
      expect(adapter.requests.single.method, 'DELETE');
      expect(
        adapter.requests.single.headers['Authorization'],
        'Bearer guest-token',
      );
    });

    test('백업 코드 확인은 저장된 토큰이 아니라 받은 토큰으로 /me/stats 를 부른다', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({
          'puzzle_language': 'ko',
          'current_streak': 3,
          'max_streak': 9,
          'solved_count': 20,
          'linked_account': {'provider': 'apple', 'email': 'a@b.com'},
        }, 200),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      final stats = await client.fetchMyStatsWithToken('backup-code');

      expect(stats.currentStreak, 3);
      expect(stats.linkedAccount?.provider, 'apple');
      expect(adapter.requests.single.path, '/me/stats');
      expect(
        adapter.requests.single.headers['Authorization'],
        'Bearer backup-code',
      );
    });

    test('틀린 백업 코드는 401 이라 UnauthorizedApiException 이다', () async {
      final adapter = _RecordingAdapter(
        (_) => _json({
          'code': 'UNAUTHORIZED',
          'message': '게스트를 찾을 수 없습니다.',
        }, 401),
      );
      final client = _clientWith(adapter, token: 'guest-token');

      await expectLater(
        client.fetchMyStatsWithToken('nope'),
        throwsA(isA<UnauthorizedApiException>()),
      );
    });

    test('빈 백업 코드는 서버까지 가지 않는다', () async {
      final adapter = _RecordingAdapter((_) => _json(const {}, 200));
      final client = _clientWith(adapter, token: 'guest-token');

      await expectLater(
        client.fetchMyStatsWithToken('  '),
        throwsA(isA<UnauthorizedApiException>()),
      );
      expect(adapter.requests, isEmpty);
    });
  });

  test('POST /subscriptions/verify 는 스토어·영수증을 보내고 권한을 돌려준다', () async {
    final adapter = _RecordingAdapter(
      (_) => _json({
        'active': true,
        'until': '2026-11-01T00:00:00+00:00',
        'status': 'active',
        'source': 'google',
        'next_check_at': '2026-10-15T04:00:00+00:00',
      }, 200),
    );
    final client = _clientWith(adapter, token: 'guest-token');

    final entitlement = await client.verifySubscription(
      store: SubscriptionStore.google,
      receipt: 'purchase-token',
    );

    expect(entitlement.active, isTrue);
    expect(entitlement.until, DateTime.utc(2026, 11));
    final request = adapter.requests.single;
    expect(request.path, '/subscriptions/verify');
    expect(request.method, 'POST');
    expect(request.data, {'store': 'google', 'receipt': 'purchase-token'});
    expect(request.headers['Authorization'], 'Bearer guest-token');
  });

  test('영수증을 인정하지 않으면 RECEIPT_INVALID 예외다 — 재시도하지 않는 쪽', () async {
    final adapter = _RecordingAdapter(
      (_) => _json({
        'code': 'RECEIPT_INVALID',
        'message': '영수증을 확인할 수 없습니다.',
      }, 400),
    );
    final client = _clientWith(adapter, token: 'guest-token');

    await expectLater(
      client.verifySubscription(
        store: SubscriptionStore.apple,
        receipt: 'bad-jws',
      ),
      throwsA(isA<ReceiptInvalidApiException>()),
    );
  });

  test('스토어가 답을 못 주면 STORE_UNAVAILABLE 예외다 — 다음 시작에 다시 올린다', () async {
    final adapter = _RecordingAdapter(
      (_) => _json({
        'code': 'STORE_UNAVAILABLE',
        'message': '스토어에 연결할 수 없습니다.',
      }, 503),
    );
    final client = _clientWith(adapter, token: 'guest-token');

    await expectLater(
      client.verifySubscription(
        store: SubscriptionStore.apple,
        receipt: 'jws',
      ),
      // 503 이라도 `code` 가 먼저다 — 호출부가 ServerApiException 과 구별해
      // "일시적 스토어 장애" 문구를 고른다.
      throwsA(isA<StoreUnavailableApiException>()),
    );
  });
}
