import 'package:chosung/api/api_client.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:dio/dio.dart';

/// 지금 유효한 게스트 토큰을 읽어온다. 토큰 상태는 Riverpod provider 가
/// 들고 있고(`guestTokenProvider`) ApiClient 는 매 요청마다 그 값을 본다 —
/// 토큰 교체(티켓 29)가 ApiClient 를 다시 만들지 않아도 되게 하려는 분리다.
typedef TokenReader = String? Function();

class DioApiClient implements ApiClient {
  DioApiClient({required Dio dio, required TokenReader readToken})
    : _dio = dio,
      _readToken = readToken;

  /// 운영 설정값으로 Dio 를 조립한다. `baseUrl` 은 `--dart-define=API_BASE_URL`.
  factory DioApiClient.withBaseUrl({
    required String baseUrl,
    required TokenReader readToken,
  }) => DioApiClient(
    dio: Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 5),
        receiveTimeout: const Duration(seconds: 10),
        contentType: Headers.jsonContentType,
      ),
    ),
    readToken: readToken,
  );

  final Dio _dio;
  final TokenReader _readToken;

  @override
  Future<String> createGuest({required PuzzleLanguage puzzleLanguage}) async {
    final body = await _send<Map<String, dynamic>>(
      () => _dio.post<Map<String, dynamic>>(
        '/guests',
        data: {'puzzle_language': puzzleLanguage.wire},
      ),
    );
    return body['token'] as String;
  }

  @override
  Future<AppConfig> fetchConfig() async {
    final body = await _send<Map<String, dynamic>>(
      () => _dio.get<Map<String, dynamic>>('/config'),
    );
    return AppConfig.fromJson(body);
  }

  @override
  Future<MyStats> fetchMyStats() async {
    final body = await _send<Map<String, dynamic>>(
      () => _dio.get<Map<String, dynamic>>('/me/stats', options: _authorized()),
    );
    return MyStats.fromJson(body);
  }

  @override
  Future<TodayPuzzle> fetchTodayPuzzle() async {
    final body = await _send<Map<String, dynamic>>(
      () => _dio.get<Map<String, dynamic>>(
        '/puzzles/today',
        options: _authorized(),
      ),
    );
    return TodayPuzzle.fromJson(body);
  }

  @override
  Future<GuessResult> submitGuess({
    required int puzzleId,
    required String guess,
  }) async {
    final body = await _send<Map<String, dynamic>>(
      () => _dio.post<Map<String, dynamic>>(
        '/puzzles/today/guesses',
        data: {'puzzle_id': puzzleId, 'guess': guess},
        options: _authorized(),
      ),
    );
    return GuessResult.fromJson(body);
  }

  @override
  Future<String> unlockHint({required int puzzleId}) async {
    final body = await _send<Map<String, dynamic>>(
      () => _dio.post<Map<String, dynamic>>(
        '/puzzles/today/hint-unlock',
        data: {'puzzle_id': puzzleId},
        options: _authorized(),
      ),
    );
    return body['hint'] as String;
  }

  @override
  Future<TodayStats> fetchTodayStats({
    required PuzzleLanguage language,
  }) async {
    final body = await _send<Map<String, dynamic>>(
      () => _dio.get<Map<String, dynamic>>(
        '/puzzles/today/stats',
        queryParameters: {'language': language.wire},
        options: _authorized(),
      ),
    );
    return TodayStats.fromJson(body);
  }

  @override
  Future<PuzzleLanguage> updatePuzzleLanguage(
    PuzzleLanguage puzzleLanguage,
  ) async {
    final body = await _send<Map<String, dynamic>>(
      () => _dio.patch<Map<String, dynamic>>(
        '/me',
        data: {'puzzle_language': puzzleLanguage.wire},
        options: _authorized(),
      ),
    );
    return PuzzleLanguage.fromWire(body['puzzle_language'] as String?) ??
        puzzleLanguage;
  }

  @override
  Future<Leaderboard> fetchTodayLeaderboard({int limit = 20}) async {
    final body = await _send<Map<String, dynamic>>(
      () => _dio.get<Map<String, dynamic>>(
        '/puzzles/today/leaderboard',
        queryParameters: {'limit': limit},
        options: _authorized(),
      ),
    );
    return Leaderboard.fromJson(body);
  }

  @override
  Future<List<HistoryDay>> fetchMyHistory({int days = 7}) async {
    // 이 엔드포인트만 최상위가 객체가 아니라 배열이다.
    final body = await _send<List<dynamic>>(
      () => _dio.get<List<dynamic>>(
        '/me/history',
        queryParameters: {'days': days},
        options: _authorized(),
      ),
    );
    return body
        .map((day) => HistoryDay.fromJson(day as Map<String, dynamic>))
        .toList(growable: false);
  }

  @override
  Future<String> exchangeIdToken({
    required String provider,
    required String idToken,
    String? authorizationCode,
  }) async {
    final body = await _send<Map<String, dynamic>>(
      () => _dio.post<Map<String, dynamic>>(
        '/auth/token-exchange',
        data: {
          'provider': provider,
          'id_token': idToken,
          // 구글은 보낼 게 없다 — null 이면 키 자체가 빠진다(null-aware element).
          'authorization_code': ?authorizationCode,
        },
        options: _authorized(),
      ),
    );
    return body['token'] as String;
  }

  @override
  Future<Entitlement> verifySubscription({
    required SubscriptionStore store,
    required String receipt,
  }) async {
    final body = await _send<Map<String, dynamic>>(
      () => _dio.post<Map<String, dynamic>>(
        '/subscriptions/verify',
        data: {'store': store.wire, 'receipt': receipt},
        options: _authorized(),
      ),
    );
    return Entitlement.fromJson(body);
  }

  @override
  Future<void> deleteAccount() async {
    try {
      // 204 라 본문이 없다 — `_send` 의 `response.data!` 를 타면 안 된다.
      await _dio.delete<void>('/me', options: _authorized());
    } on DioException catch (error) {
      throw _toApiException(error);
    }
  }

  @override
  Future<MyStats> fetchMyStatsWithToken(String token) async {
    final body = await _send<Map<String, dynamic>>(
      () => _dio.get<Map<String, dynamic>>(
        '/me/stats',
        options: _bearer(token),
      ),
    );
    return MyStats.fromJson(body);
  }

  /// Bearer 가 필요한 호출은 토큰이 없으면 서버까지 가지 않고 401 과 같은
  /// 예외를 낸다 — 호출부가 "토큰 없음" 과 "토큰 만료" 를 따로 다룰 이유가 없다.
  Options _authorized() => _bearer(_readToken());

  /// 빈 토큰은 서버까지 보내지 않는다 — 401 이 올 게 뻔하고, 백업 코드 입력이
  /// 공백뿐일 때도 같은 자리에서 걸린다.
  Options _bearer(String? token) {
    final bearer = token?.trim() ?? '';
    if (bearer.isEmpty) {
      throw const UnauthorizedApiException(
        code: 'UNAUTHORIZED',
        message: '게스트 토큰이 없습니다.',
      );
    }
    return Options(headers: {'Authorization': 'Bearer $bearer'});
  }

  Future<T> _send<T>(Future<Response<T>> Function() request) async {
    try {
      final response = await request();
      return response.data!;
    } on DioException catch (error) {
      throw _toApiException(error);
    }
  }

  ApiException _toApiException(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.transformTimeout:
      case DioExceptionType.connectionError:
      case DioExceptionType.cancel:
        return NetworkApiException(
          code: networkErrorCode,
          message: error.message ?? '네트워크에 연결할 수 없습니다.',
        );
      case DioExceptionType.badCertificate:
      case DioExceptionType.badResponse:
      case DioExceptionType.unknown:
        final body = error.response?.data;
        final payload = body is Map<String, dynamic>
            ? body
            : const <String, dynamic>{};
        return apiExceptionOf(
          code: payload['code'] as String? ?? unknownErrorCode,
          message: payload['message'] as String? ?? '알 수 없는 오류가 발생했습니다.',
          statusCode: error.response?.statusCode,
        );
    }
  }
}
