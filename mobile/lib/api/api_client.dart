import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';

/// 서버 API 중 **지금 앱이 실제로 쓰는 것**만 둔다.
///
/// 스펙 §A' 의 나머지 메서드는 그걸 호출하는 티켓(27·29·30·31)이 더한다 —
/// 쓰지 않는 메서드를 미리 선언하면 가짜 구현만 늘고 테스트가 증명하는 건 없다.
abstract interface class ApiClient {
  /// `POST /guests` → 새 게스트 토큰.
  Future<String> createGuest({required PuzzleLanguage puzzleLanguage});

  /// `GET /config` → 점검·최소 버전·지원 언어·스토어 링크. 인증 없음.
  Future<AppConfig> fetchConfig();

  /// `GET /me/stats` → 내 기록. Bearer 게스트 토큰 필요.
  Future<MyStats> fetchMyStats();

  /// `GET /puzzles/today` → 오늘 퍼즐 + 내 시도 이력. 보드의 정본이다.
  /// 그 언어의 퍼즐이 아직 없으면 [NoPuzzleTodayApiException].
  Future<TodayPuzzle> fetchTodayPuzzle();

  /// `POST /puzzles/today/guesses` → 판정·피드백. 화면에 그린 퍼즐의
  /// [puzzleId] 를 같이 보내고, 서버의 "지금의 오늘" 과 다르면
  /// [PuzzleChangedApiException] 이 온다(시도는 소비되지 않는다).
  Future<GuessResult> submitGuess({
    required int puzzleId,
    required String guess,
  });

  /// `PATCH /me` → 바뀐 퍼즐 언어. 설정 화면(티켓 29·30)이 쓴다.
  Future<PuzzleLanguage> updatePuzzleLanguage(PuzzleLanguage puzzleLanguage);
}
