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

/// 위 어디에도 안 맞는 응답. 화면은 "알 수 없는 오류 + 재시도" 로 다룬다.
class UnknownApiException extends ApiException {
  const UnknownApiException({required super.code, required super.message});
}

const String unknownErrorCode = 'UNKNOWN_ERROR';
const String networkErrorCode = 'NETWORK_ERROR';

/// 서버 `code` → 예외 타입. 뒤 티켓(23·24·25·27·29·30)이 자기 코드를 더한다.
const Map<
  String,
  ApiException Function({required String code, required String message})
>
_exceptionsByCode = {
  'UNAUTHORIZED': UnauthorizedApiException.new,
  'VALIDATION_ERROR': ValidationApiException.new,
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
