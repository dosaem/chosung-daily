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
  });
}
