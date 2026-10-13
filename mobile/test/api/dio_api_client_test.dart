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
}
