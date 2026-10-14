import 'dart:async';

import 'package:chosung/api/api_client.dart';
import 'package:chosung/api/api_models.dart';

AppConfig fakeAppConfig({
  String minIos = '1.0.0',
  String minAndroid = '1.0.0',
  bool maintenance = false,
  String? maintenanceMessage,
  List<PuzzleLanguage> languages = PuzzleLanguage.values,
  String? storeUrlIos,
  String? storeUrlAndroid,
}) => AppConfig(
  minAppVersion: MinAppVersion(ios: minIos, android: minAndroid),
  maintenance: Maintenance(enabled: maintenance, message: maintenanceMessage),
  languages: languages,
  storeUrls: StoreUrls(ios: storeUrlIos, android: storeUrlAndroid),
);

MyStats fakeMyStats({
  PuzzleLanguage puzzleLanguage = PuzzleLanguage.ko,
  int currentStreak = 0,
  int maxStreak = 0,
  int solvedCount = 0,
  LinkedAccount? linkedAccount,
}) => MyStats(
  puzzleLanguage: puzzleLanguage,
  currentStreak: currentStreak,
  maxStreak: maxStreak,
  solvedCount: solvedCount,
  linkedAccount: linkedAccount,
);

/// ko "지하철역" 의 가림 — 초성 4개가 보이는 타일이다.
const fakeKoMask = [
  MaskTile(type: MaskTileType.revealed, char: 'ㅈ'),
  MaskTile(type: MaskTileType.revealed, char: 'ㅎ'),
  MaskTile(type: MaskTileType.revealed, char: 'ㅊ'),
  MaskTile(type: MaskTileType.revealed, char: 'ㅇ'),
];

/// `length` 는 구분자를 뺀 타일 수라 mask 에서 계산한다 — 두 값을 따로 받으면
/// 서버가 절대 보내지 않는 조합(타일 4개 + length 2)으로 테스트를 쓸 수 있다.
TodayPuzzle fakeTodayPuzzle({
  int puzzleId = 1,
  DateTime? date,
  PuzzleLanguage language = PuzzleLanguage.ko,
  List<MaskTile> mask = fakeKoMask,
  WordCategory category = WordCategory.general,
  int attemptsLeft = 5,
  List<PuzzleAttempt> attempts = const [],
  PuzzleStatus status = PuzzleStatus.inProgress,
  bool hintUnlocked = false,
  String? hint,
  String? answer,
}) => TodayPuzzle(
  puzzleId: puzzleId,
  date: date ?? DateTime(2026, 10, 13),
  language: language,
  mask: mask,
  length: mask.where((tile) => tile.type != MaskTileType.separator).length,
  category: category,
  attemptsLeft: attemptsLeft,
  attempts: attempts,
  status: status,
  hintUnlocked: hintUnlocked,
  hint: hint,
  answer: answer,
);

GuessResult fakeGuessResult({
  bool isCorrect = false,
  int attemptsLeft = 4,
  List<bool>? feedback = const [true, false, false, true],
  String? hint,
  String? answer,
}) => GuessResult(
  isCorrect: isCorrect,
  attemptsLeft: attemptsLeft,
  feedback: isCorrect ? null : feedback,
  hint: hint,
  answer: answer,
);

TodayStats fakeTodayStats({
  DateTime? date,
  PuzzleLanguage language = PuzzleLanguage.ko,
  int totalSolved = 100,
  Map<int, double> byAttempt = const {
    1: 0.08,
    2: 0.31,
    3: 0.4,
    4: 0.15,
    5: 0.06,
  },
}) => TodayStats(
  date: date ?? DateTime(2026, 10, 13),
  language: language,
  totalSolved: totalSolved,
  byAttempt: byAttempt,
);

LeaderboardEntry fakeLeaderboardEntry({
  required int rank,
  String? display,
  int attempts = 1,
  int seconds = 41,
  bool isMe = false,
}) => LeaderboardEntry(
  rank: rank,
  display: display ?? '게스트 #${rank.toRadixString(16).padLeft(4, '0')}',
  attempts: attempts,
  seconds: seconds,
  isMe: isMe,
);

Leaderboard fakeLeaderboard({
  DateTime? date,
  PuzzleLanguage language = PuzzleLanguage.ko,
  List<LeaderboardEntry>? entries,
  MyRank? me,
}) => Leaderboard(
  date: date ?? DateTime(2026, 10, 13),
  language: language,
  entries: entries ?? const [],
  me: me,
);

/// 서버와 같은 순서(오래된 날짜부터)로 7일을 만든다. [results] 는 그 순서대로
/// 날짜 하나씩 받고, 모자라면 미플레이로 채운다.
List<HistoryDay> fakeHistory({
  DateTime? lastDate,
  int days = 7,
  List<Map<PuzzleLanguage, DayResult>> results = const [],
}) {
  final last = lastDate ?? DateTime(2026, 10, 13);
  return [
    for (var offset = days - 1; offset >= 0; offset--)
      HistoryDay(
        date: last.subtract(Duration(days: offset)),
        results:
            results.elementAtOrNull(days - 1 - offset) ??
            {
              for (final language in PuzzleLanguage.values)
                language: DayResult.none,
            },
      ),
  ];
}

/// 테스트용 [ApiClient]. 서버가 돌려줄 값을 그대로 들고 있고, 호출 횟수와
/// 보낸 인자를 기록한다. 응답을 바꾸려면 필드를 다시 넣으면 된다.
class FakeApiClient implements ApiClient {
  FakeApiClient({
    AppConfig? config,
    MyStats? stats,
    TodayPuzzle? puzzle,
    GuessResult? guessResult,
    TodayStats? todayStats,
    Leaderboard? leaderboard,
    List<HistoryDay>? history,
    this.nextGuestToken = 'fake-guest-token',
  }) : config = config ?? fakeAppConfig(),
       stats = stats ?? fakeMyStats(),
       puzzle = puzzle ?? fakeTodayPuzzle(),
       guessResult = guessResult ?? fakeGuessResult(),
       todayStats = todayStats ?? fakeTodayStats(),
       leaderboard = leaderboard ?? fakeLeaderboard(),
       history = history ?? fakeHistory();

  AppConfig config;
  MyStats stats;
  TodayPuzzle puzzle;
  GuessResult guessResult;
  TodayStats todayStats;
  Leaderboard leaderboard;
  List<HistoryDay> history;
  String nextGuestToken;

  /// 넣어두면 그 호출이 이 예외를 던진다.
  Exception? createGuestError;
  Exception? fetchConfigError;
  Exception? fetchMyStatsError;
  Exception? fetchTodayPuzzleError;
  Exception? submitGuessError;
  Exception? fetchTodayStatsError;
  Exception? fetchTodayLeaderboardError;
  Exception? fetchMyHistoryError;
  Exception? updatePuzzleLanguageError;

  /// 넣어두면 이 Completer 가 끝날 때까지 오늘 퍼즐 응답을 붙잡는다 —
  /// "로딩 중(스켈레톤)" 화면을 그 상태로 세워두고 보는 데 쓴다.
  Completer<void>? fetchTodayPuzzleGate;

  /// 같은 방식으로 제출 응답을 붙잡는다 — 제출이 날아간 뒤 응답이 오기 전에
  /// 재조회가 끼어드는 순서를 테스트가 직접 만들어 보는 데 쓴다.
  Completer<void>? submitGuessGate;

  /// 분포 응답도 붙잡을 수 있다 — 결과 시트의 통계 스켈레톤을 세워 두는 데 쓴다.
  Completer<void>? fetchTodayStatsGate;

  final List<PuzzleLanguage> createGuestLanguages = [];
  int fetchConfigCalls = 0;
  int fetchMyStatsCalls = 0;
  int fetchTodayPuzzleCalls = 0;
  int fetchTodayStatsCalls = 0;

  /// `fetchTodayStats` 가 받은 언어들 — 시트가 "지금 선호 언어" 가 아니라
  /// 그린 퍼즐의 언어로 묻는지 보려고 기록한다.
  final List<PuzzleLanguage> fetchTodayStatsLanguages = [];
  final List<int> fetchTodayLeaderboardLimits = [];
  final List<int> fetchMyHistoryDays = [];

  /// 제출로 보낸 (puzzle_id, guess) 를 순서대로 기록한다 — `puzzle_id` 동봉은
  /// 409 흐름의 전제라 테스트가 직접 본다.
  final List<({int puzzleId, String guess})> submittedGuesses = [];
  final List<PuzzleLanguage> updatedPuzzleLanguages = [];

  int get createGuestCalls => createGuestLanguages.length;

  @override
  Future<String> createGuest({required PuzzleLanguage puzzleLanguage}) async {
    createGuestLanguages.add(puzzleLanguage);
    if (createGuestError case final error?) throw error;
    return nextGuestToken;
  }

  @override
  Future<AppConfig> fetchConfig() async {
    fetchConfigCalls++;
    if (fetchConfigError case final error?) throw error;
    return config;
  }

  @override
  Future<MyStats> fetchMyStats() async {
    fetchMyStatsCalls++;
    if (fetchMyStatsError case final error?) throw error;
    return stats;
  }

  @override
  Future<TodayPuzzle> fetchTodayPuzzle() async {
    fetchTodayPuzzleCalls++;
    // 응답은 **호출 시점의** 값이다 — 붙잡아 둔 조회가 그 사이 바뀐 `puzzle` 을
    // 돌려주면 "늦게 도착한 옛 응답" 을 테스트가 만들 수 없다.
    final response = puzzle;
    if (fetchTodayPuzzleGate case final gate?) await gate.future;
    if (fetchTodayPuzzleError case final error?) throw error;
    return response;
  }

  @override
  Future<GuessResult> submitGuess({
    required int puzzleId,
    required String guess,
  }) async {
    submittedGuesses.add((puzzleId: puzzleId, guess: guess));
    if (submitGuessGate case final gate?) await gate.future;
    if (submitGuessError case final error?) throw error;
    return guessResult;
  }

  @override
  Future<TodayStats> fetchTodayStats({
    required PuzzleLanguage language,
  }) async {
    fetchTodayStatsCalls++;
    fetchTodayStatsLanguages.add(language);
    if (fetchTodayStatsGate case final gate?) await gate.future;
    if (fetchTodayStatsError case final error?) throw error;
    return todayStats;
  }

  @override
  Future<PuzzleLanguage> updatePuzzleLanguage(
    PuzzleLanguage puzzleLanguage,
  ) async {
    updatedPuzzleLanguages.add(puzzleLanguage);
    if (updatePuzzleLanguageError case final error?) throw error;
    return puzzleLanguage;
  }

  @override
  Future<Leaderboard> fetchTodayLeaderboard({int limit = 20}) async {
    fetchTodayLeaderboardLimits.add(limit);
    if (fetchTodayLeaderboardError case final error?) throw error;
    return leaderboard;
  }

  @override
  Future<List<HistoryDay>> fetchMyHistory({int days = 7}) async {
    fetchMyHistoryDays.add(days);
    if (fetchMyHistoryError case final error?) throw error;
    return history;
  }
}
