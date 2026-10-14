import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';

/// 서버 API 중 **지금 앱이 실제로 쓰는 것**만 둔다.
///
/// 스펙 §A' 의 나머지 메서드는 그걸 호출하는 티켓(29·32·33)이 더한다 —
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

  /// `POST /puzzles/today/hint-unlock` → 힌트 문장. 보상형 광고를 끝까지 본
  /// 비구독자와 구독자가 같은 호출을 쓴다 — 서버는 광고 시청 여부를 알 수 없고
  /// (AdMob SSV 미사용, README "06. 힌트 미리 보기 공정성") "퍼즐당 한 번" 과
  /// "시도·순위에 영향 없음" 만 지킨다.
  ///
  /// 이미 열었으면 409 [HintAlreadyUnlockedApiException], 끝난 퍼즐이면 409
  /// [AlreadyFinishedApiException], 보고 있던 퍼즐이 "지금의 오늘" 과 다르면
  /// 409 [PuzzleChangedApiException].
  Future<String> unlockHint({required int puzzleId});

  /// `GET /puzzles/today/stats?language=` → 그 언어 오늘 퍼즐의 시도별 정답자
  /// 비율. 결과 시트(S2)가 쓴다. 그 언어의 퍼즐이 아직 없으면
  /// [NoPuzzleTodayApiException].
  ///
  /// [language] 는 필수다 — 생략하면 서버가 **요청 시점의 게스트 선호 언어**로
  /// 집계를 고르므로, 다른 기기에서 언어를 바꾸면 내가 푼 퍼즐과 다른 언어의
  /// 분포가 온다(스펙 §A' `GET /puzzles/today/stats?language=`).
  Future<TodayStats> fetchTodayStats({required PuzzleLanguage language});

  /// `PATCH /me` → 바뀐 퍼즐 언어. S4 설정의 퍼즐 언어 행이 쓴다.
  Future<PuzzleLanguage> updatePuzzleLanguage(PuzzleLanguage puzzleLanguage);

  /// `GET /puzzles/today/leaderboard` → 오늘 상위 [limit] 명 + 내 순위.
  /// 언어는 보내지 않는다 — 서버가 게스트 선호 언어로 고르고, S3 의 언어 칩은
  /// 그 응답을 보여주기만 한다(전환은 S4 설정).
  Future<Leaderboard> fetchTodayLeaderboard({int limit});

  /// `GET /me/history?days=` → 최근 [days] 일의 언어별 결과(오래된 날짜부터).
  Future<List<HistoryDay>> fetchMyHistory({int days});

  /// `POST /auth/token-exchange` → 연결·전환된 게스트의 토큰(스펙 §A.6).
  ///
  /// [authorizationCode] 는 애플만 보낸다 — 서버가 그걸로 refresh token 을
  /// 받아 두고, 계정 삭제 때 애플 쪽 연결을 철회한다(§A.7).
  ///
  /// 돌아온 토큰이 지금 쓰던 토큰과 **다르면 다른 기기의 기록으로 전환된
  /// 것**이고, 같으면 지금 게스트에 계정이 새로 붙은 것이다.
  Future<String> exchangeIdToken({
    required String provider,
    required String idToken,
    String? authorizationCode,
  });

  /// `DELETE /me` → 계정·기록 전부 삭제(204). 그 뒤 이 토큰은 401 이다.
  Future<void> deleteAccount();

  /// `GET /me/stats` 를 **[token] 으로** 부른다. 백업 코드(= 다른 기기의 게스트
  /// 토큰)가 아직 살아 있는지 확인하는 용도라, 저장된 토큰을 쓰는
  /// [fetchMyStats] 와 달리 토큰을 인자로 받는다. 200 이면 쓸 수 있는 코드고
  /// 401 이면 아니다 — 백업 코드 전용 엔드포인트는 만들지 않는다(티켓 29).
  Future<MyStats> fetchMyStatsWithToken(String token);
}
