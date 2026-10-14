/// 서버 에러 응답(`{code, message}`)과 전송 실패를 앱 쪽 예외로 옮긴다.
///
/// 화면은 `code` 문자열을 보지 않고 예외 타입으로 분기한다 — 이 티켓이 쓰는
/// 세 엔드포인트가 낼 수 있는 것만 타입을 뒀고, 뒤 티켓이 새 코드를 쓸 때
/// [_exceptionsByCode] 에 한 줄을 더한다.
sealed class ApiException implements Exception {
  const ApiException({required this.code, required this.message});

  final String code;
  final String message;

  @override
  String toString() => 'ApiException($code): $message';
}

/// 게스트 토큰이 없거나 더 이상 유효하지 않다 → 새 게스트를 발급해야 한다.
class UnauthorizedApiException extends ApiException {
  const UnauthorizedApiException({required super.code, required super.message});
}

/// 요청 값이 서버 검증을 통과하지 못했다. 재시도해도 같은 결과다.
class ValidationApiException extends ApiException {
  const ValidationApiException({required super.code, required super.message});
}

/// 5xx·점검 등 서버 쪽 사정. 재시도가 의미 있다.
class ServerApiException extends ApiException {
  const ServerApiException({required super.code, required super.message});
}

/// 연결·타임아웃·취소. 오프라인 배너와 재시도 버튼의 근거.
class NetworkApiException extends ApiException {
  const NetworkApiException({required super.code, required super.message});
}

/// 오늘 그 언어의 퍼즐이 아직 배정되지 않았다(자정 전환 직후). 화면은 빈
/// 화면·에러가 아니라 "곧 새 퍼즐" 카운트다운 카드를 보여준다(OVERRIDES §7).
class NoPuzzleTodayApiException extends ApiException {
  const NoPuzzleTodayApiException({
    required super.code,
    required super.message,
  });
}

/// 보고 있던 퍼즐이 "지금의 오늘 × 현재 언어" 와 다르다. 시도는 소비되지
/// 않았고(README "04. `puzzle_id` 고정과 409 `PUZZLE_CHANGED`") 할 일은
/// `GET /puzzles/today` 재조회 하나뿐이다.
class PuzzleChangedApiException extends ApiException {
  const PuzzleChangedApiException({
    required super.code,
    required super.message,
  });
}

/// 앱이 보낸 `id_token` 을 서버가 검증하지 못했다(401 `INVALID_ID_TOKEN`).
/// 토큰 만료와 달리 **지금 게스트 토큰은 멀쩡하다** — 새 게스트를 발급하면
/// 안 되고, 로그인을 다시 시도하라고만 말한다.
class InvalidIdTokenApiException extends ApiException {
  const InvalidIdTokenApiException({
    required super.code,
    required super.message,
  });
}

/// 지금 게스트에 이미 다른 계정이 연결돼 있다(409 `ACCOUNT_ALREADY_LINKED`).
class AccountAlreadyLinkedApiException extends ApiException {
  const AccountAlreadyLinkedApiException({
    required super.code,
    required super.message,
  });
}

/// 위 어디에도 안 맞는 응답. 화면은 "알 수 없는 오류 + 재시도" 로 다룬다.
class UnknownApiException extends ApiException {
  const UnknownApiException({required super.code, required super.message});
}

const String unknownErrorCode = 'UNKNOWN_ERROR';
const String networkErrorCode = 'NETWORK_ERROR';

/// 서버 `code` → 예외 타입. 뒤 티켓(30·31·32)이 자기 코드를 더한다.
const Map<
  String,
  ApiException Function({required String code, required String message})
>
_exceptionsByCode = {
  'UNAUTHORIZED': UnauthorizedApiException.new,
  'VALIDATION_ERROR': ValidationApiException.new,
  'NO_PUZZLE_TODAY': NoPuzzleTodayApiException.new,
  'PUZZLE_CHANGED': PuzzleChangedApiException.new,
  'INVALID_ID_TOKEN': InvalidIdTokenApiException.new,
  'ACCOUNT_ALREADY_LINKED': AccountAlreadyLinkedApiException.new,
};

/// `code` 를 모를 때(본문이 JSON 이 아닌 경우 포함) HTTP status 로 떨어뜨린다.
ApiException apiExceptionOf({
  required String code,
  required String message,
  required int? statusCode,
}) {
  final byCode = _exceptionsByCode[code];
  if (byCode != null) return byCode(code: code, message: message);

  if (statusCode == 401) {
    return UnauthorizedApiException(code: code, message: message);
  }
  if (statusCode != null && statusCode >= 500) {
    return ServerApiException(code: code, message: message);
  }
  return UnknownApiException(code: code, message: message);
}
