import 'package:chosung/api/api_models.dart';

/// 서버 API 중 **이 티켓(22)이 실제로 쓰는 세 개**만 둔다.
///
/// 스펙 §A' 의 나머지 메서드는 그걸 호출하는 티켓(23·24·25·27·29·30)이 더한다 —
/// 쓰지 않는 메서드를 미리 선언하면 가짜 구현만 늘고 테스트가 증명하는 건 없다.
abstract interface class ApiClient {
  /// `POST /guests` → 새 게스트 토큰.
  Future<String> createGuest({required PuzzleLanguage puzzleLanguage});

  /// `GET /config` → 점검·최소 버전·지원 언어·스토어 링크. 인증 없음.
  Future<AppConfig> fetchConfig();

  /// `GET /me/stats` → 내 기록. Bearer 게스트 토큰 필요.
  Future<MyStats> fetchMyStats();
}
