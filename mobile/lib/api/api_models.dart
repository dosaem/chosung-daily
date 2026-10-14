import 'package:flutter/foundation.dart';

/// 퍼즐 언어. 서버 `PuzzleLanguage` enum 과 wire 값이 같다.
enum PuzzleLanguage {
  ko('ko'),
  en('en')
  ;

  const PuzzleLanguage(this.wire);

  final String wire;

  static PuzzleLanguage? fromWire(String? value) {
    for (final language in PuzzleLanguage.values) {
      if (language.wire == value) return language;
    }
    return null;
  }

  /// 게스트를 처음 발급할 때 쓰는 기본 언어 — 기기 언어가 영어면 en, 나머지는 ko.
  static PuzzleLanguage forDeviceLanguage(String languageCode) =>
      languageCode == PuzzleLanguage.en.wire
      ? PuzzleLanguage.en
      : PuzzleLanguage.ko;
}

@immutable
class MinAppVersion {
  const MinAppVersion({required this.ios, required this.android});

  factory MinAppVersion.fromJson(Map<String, dynamic> json) => MinAppVersion(
    ios: json['ios'] as String,
    android: json['android'] as String,
  );

  final String ios;
  final String android;
}

@immutable
class Maintenance {
  const Maintenance({required this.enabled, this.message});

  factory Maintenance.fromJson(Map<String, dynamic> json) => Maintenance(
    enabled: json['enabled'] as bool,
    message: json['message'] as String?,
  );

  final bool enabled;
  final String? message;
}

/// 스토어 등록 전에는 둘 다 null 이다(서버 환경변수가 비어 있음).
@immutable
class StoreUrls {
  const StoreUrls({this.ios, this.android});

  factory StoreUrls.fromJson(Map<String, dynamic> json) => StoreUrls(
    ios: json['ios'] as String?,
    android: json['android'] as String?,
  );

  final String? ios;
  final String? android;
}

/// `GET /api/v1/config` 응답.
@immutable
class AppConfig {
  const AppConfig({
    required this.minAppVersion,
    required this.maintenance,
    required this.languages,
    required this.storeUrls,
  });

  factory AppConfig.fromJson(Map<String, dynamic> json) => AppConfig(
    minAppVersion: MinAppVersion.fromJson(
      json['min_app_version'] as Map<String, dynamic>,
    ),
    maintenance: Maintenance.fromJson(
      json['maintenance'] as Map<String, dynamic>,
    ),
    // 서버가 앱보다 먼저 언어를 늘릴 수 있으므로 모르는 코드는 버린다.
    languages: (json['languages'] as List<dynamic>)
        .map((value) => PuzzleLanguage.fromWire(value as String?))
        .nonNulls
        .toList(growable: false),
    storeUrls: StoreUrls.fromJson(json['store_urls'] as Map<String, dynamic>),
  );

  final MinAppVersion minAppVersion;
  final Maintenance maintenance;
  final List<PuzzleLanguage> languages;
  final StoreUrls storeUrls;
}

@immutable
class LinkedAccount {
  const LinkedAccount({required this.provider, this.email});

  factory LinkedAccount.fromJson(Map<String, dynamic> json) => LinkedAccount(
    provider: json['provider'] as String,
    email: json['email'] as String?,
  );

  final String provider;
  final String? email;
}

/// `GET /api/v1/me/stats` 응답. `entitlement` 는 구독 티켓(30·31)이 더한다.
@immutable
class MyStats {
  const MyStats({
    required this.puzzleLanguage,
    required this.currentStreak,
    required this.maxStreak,
    required this.solvedCount,
    this.linkedAccount,
  });

  factory MyStats.fromJson(Map<String, dynamic> json) {
    final account = json['linked_account'] as Map<String, dynamic>?;
    return MyStats(
      puzzleLanguage:
          PuzzleLanguage.fromWire(json['puzzle_language'] as String?) ??
          PuzzleLanguage.ko,
      currentStreak: json['current_streak'] as int,
      maxStreak: json['max_streak'] as int,
      solvedCount: json['solved_count'] as int,
      linkedAccount: account == null ? null : LinkedAccount.fromJson(account),
    );
  }

  final PuzzleLanguage puzzleLanguage;
  final int currentStreak;
  final int maxStreak;
  final int solvedCount;
  final LinkedAccount? linkedAccount;
}

/// 가림 타일 한 칸의 종류. 서버 `app/utils/mask.py` 의 `t` 값과 같다.
enum MaskTileType {
  /// 보이는 타일 — `char` 가 화면에 찍힌다(ko 초성, en 자음).
  revealed('r'),

  /// 빈 타일 — 맞춰야 하는 글자. `char` 는 항상 빈 문자열이다.
  hidden('h'),

  /// 구분자(공백·하이픈). 타일이 아니라 타일 사이 간격이고 글자 수에 안 들어간다.
  separator('s')
  ;

  const MaskTileType(this.wire);

  final String wire;

  /// 모르는 종류는 빈 타일로 떨어뜨린다 — 서버가 앱보다 먼저 타일을 늘렸을 때
  /// 글자로 그려버리면 정답이 새어나갈 수 있다.
  static MaskTileType fromWire(String? value) {
    for (final type in MaskTileType.values) {
      if (type.wire == value) return type;
    }
    return hidden;
  }
}

@immutable
class MaskTile {
  const MaskTile({required this.type, required this.char});

  factory MaskTile.fromJson(Map<String, dynamic> json) => MaskTile(
    type: MaskTileType.fromWire(json['t'] as String?),
    char: json['c'] as String? ?? '',
  );

  final MaskTileType type;
  final String char;
}

enum WordCategory {
  general('general'),
  bookTitle('book_title')
  ;

  const WordCategory(this.wire);

  final String wire;

  /// 운영자가 카테고리를 늘려도 앱이 떠야 한다 — 모르는 값은 일반 단어로 본다.
  static WordCategory fromWire(String? value) {
    for (final category in WordCategory.values) {
      if (category.wire == value) return category;
    }
    return general;
  }

  String get labelKey => switch (this) {
    general => 'category.general',
    bookTitle => 'category.book_title',
  };
}

enum PuzzleStatus {
  inProgress('in_progress'),
  success('success'),
  fail('fail')
  ;

  const PuzzleStatus(this.wire);

  final String wire;

  static PuzzleStatus fromWire(String? value) {
    for (final status in PuzzleStatus.values) {
      if (status.wire == value) return status;
    }
    return inProgress;
  }

  /// 끝난 퍼즐은 입력 대신 "결과 보기" 를 보여준다.
  bool get isFinished => this != inProgress;
}

/// 시도 이력 한 행. `feedback` 은 구분자를 뺀 글자 수(`length`)만큼 항상 채워져
/// 온다 — 정답 행도 전부 `true` 다(README "04. 시도 이력을 서버가 돌려주는 이유").
@immutable
class PuzzleAttempt {
  const PuzzleAttempt({required this.guess, required this.feedback});

  factory PuzzleAttempt.fromJson(Map<String, dynamic> json) => PuzzleAttempt(
    guess: json['guess'] as String,
    feedback: (json['feedback'] as List<dynamic>)
        .map((value) => value as bool)
        .toList(growable: false),
  );

  final String guess;
  final List<bool> feedback;
}

/// `GET /api/v1/puzzles/today` 응답. 보드는 이 값 하나로 전부 그려진다 —
/// 로컬에 이력을 쌓지 않는다(README "04. 시도 이력을 서버가 돌려주는 이유").
@immutable
class TodayPuzzle {
  const TodayPuzzle({
    required this.puzzleId,
    required this.date,
    required this.language,
    required this.mask,
    required this.length,
    required this.category,
    required this.attemptsLeft,
    required this.attempts,
    required this.status,
    required this.hintUnlocked,
    this.hint,
    this.answer,
  });

  factory TodayPuzzle.fromJson(Map<String, dynamic> json) => TodayPuzzle(
    puzzleId: json['puzzle_id'] as int,
    // 서버가 KST 로 계산한 퍼즐 날짜다. 날짜 줄에 그대로 찍는다.
    date: DateTime.parse(json['date'] as String),
    language:
        PuzzleLanguage.fromWire(json['language'] as String?) ??
        PuzzleLanguage.ko,
    mask: (json['mask'] as List<dynamic>)
        .map((tile) => MaskTile.fromJson(tile as Map<String, dynamic>))
        .toList(growable: false),
    length: json['length'] as int,
    category: WordCategory.fromWire(json['category'] as String?),
    attemptsLeft: json['attempts_left'] as int,
    attempts: (json['attempts'] as List<dynamic>)
        .map(
          (attempt) => PuzzleAttempt.fromJson(attempt as Map<String, dynamic>),
        )
        .toList(growable: false),
    status: PuzzleStatus.fromWire(json['status'] as String?),
    hintUnlocked: json['hint_unlocked'] as bool,
    hint: json['hint'] as String?,
    answer: json['answer'] as String?,
  );

  final int puzzleId;
  final DateTime date;
  final PuzzleLanguage language;
  final List<MaskTile> mask;

  /// 구분자를 뺀 글자 수. 보드 한 행의 타일 수이자 제출 길이 검증 기준이다.
  final int length;
  final WordCategory category;
  final int attemptsLeft;
  final List<PuzzleAttempt> attempts;
  final PuzzleStatus status;
  final bool hintUnlocked;

  /// 3번째 오답 뒤 또는 힌트 미리 보기(티켓 31)를 쓴 뒤에만 채워진다.
  final String? hint;

  /// 끝난 퍼즐에만 채워진다.
  final String? answer;

  /// 입력창 최대 글자 수를 정할 때 쓴다 — en 은 구분자까지 칠 수 있다.
  int get separatorCount =>
      mask.where((tile) => tile.type == MaskTileType.separator).length;

  TodayPuzzle copyWith({
    int? attemptsLeft,
    List<PuzzleAttempt>? attempts,
    PuzzleStatus? status,
    String? hint,
    String? answer,
  }) => TodayPuzzle(
    puzzleId: puzzleId,
    date: date,
    language: language,
    mask: mask,
    length: length,
    category: category,
    attemptsLeft: attemptsLeft ?? this.attemptsLeft,
    attempts: attempts ?? this.attempts,
    status: status ?? this.status,
    hintUnlocked: hintUnlocked,
    hint: hint ?? this.hint,
    answer: answer ?? this.answer,
  );
}

/// `POST /api/v1/puzzles/today/guesses` 응답.
@immutable
class GuessResult {
  const GuessResult({
    required this.isCorrect,
    required this.attemptsLeft,
    this.feedback,
    this.hint,
    this.answer,
  });

  factory GuessResult.fromJson(Map<String, dynamic> json) => GuessResult(
    isCorrect: json['is_correct'] as bool,
    attemptsLeft: json['attempts_left'] as int,
    feedback: (json['feedback'] as List<dynamic>?)
        ?.map((value) => value as bool)
        .toList(growable: false),
    hint: json['hint'] as String?,
    answer: json['answer'] as String?,
  );

  final bool isCorrect;
  final int attemptsLeft;

  /// 정답일 때는 null 이다 — 그 행은 전부 맞음이라 서버가 따로 안 보낸다.
  final List<bool>? feedback;
  final String? hint;
  final String? answer;
}

/// `GET /api/v1/puzzles/today/stats` 응답. 결과 시트(S2)의 분포 막대가 쓴다.
@immutable
class TodayStats {
  const TodayStats({
    required this.date,
    required this.language,
    required this.totalSolved,
    required this.byAttempt,
  });

  factory TodayStats.fromJson(Map<String, dynamic> json) => TodayStats(
    date: DateTime.parse(json['date'] as String),
    language:
        PuzzleLanguage.fromWire(json['language'] as String?) ??
        PuzzleLanguage.ko,
    totalSolved: json['total_solved'] as int,
    byAttempt: {
      for (final entry in (json['by_attempt'] as Map<String, dynamic>).entries)
        // 서버가 시도 칸 말고 다른 키(예: 집계용 "fail")를 보내도 떠야 한다 —
        // 숫자가 아닌 키는 `?` 가 그 칸을 빼버린다.
        ?int.tryParse(entry.key): (entry.value as num).toDouble(),
    },
  );

  final DateTime date;
  final PuzzleLanguage language;

  /// 오늘 이 언어의 퍼즐을 맞춘 사람 수. 0 이면 분포가 전부 0 이다.
  final int totalSolved;

  /// 시도 횟수(1~5) → 그 횟수에 맞춘 사람의 비율(0~1). 서버가 안 보낸 칸은
  /// 아예 없으므로 화면이 `?? 0` 으로 읽는다.
  final Map<int, double> byAttempt;

  /// [puzzle] 의 집계인가.
  ///
  /// `/puzzles/today/stats` 는 **요청 시점의 "오늘"** 을 돌려준다 — 결과 시트를
  /// 열어 둔 채 KST 자정을 넘기면 재조회가 다음 날 분포를 가져온다. 그걸 어제
  /// 내 결과 위에 붙이지 않으려고 화면이 날짜·언어를 대조한다.
  bool isFor(TodayPuzzle puzzle) =>
      language == puzzle.language &&
      date.year == puzzle.date.year &&
      date.month == puzzle.date.month &&
      date.day == puzzle.date.day;
}

/// 리더보드 한 줄. `display` 는 서버가 만든 익명 이름("게스트 #a3f1")이다 —
/// 이메일도 게스트 ID 도 내려오지 않는다(README "07. 리더보드 익명 표시").
@immutable
class LeaderboardEntry {
  const LeaderboardEntry({
    required this.rank,
    required this.display,
    required this.attempts,
    required this.seconds,
    required this.isMe,
  });

  factory LeaderboardEntry.fromJson(Map<String, dynamic> json) =>
      LeaderboardEntry(
        rank: json['rank'] as int,
        display: json['display'] as String,
        attempts: json['attempts'] as int,
        seconds: json['seconds'] as int,
        isMe: json['is_me'] as bool,
      );

  final int rank;
  final String display;
  final int attempts;

  /// 퍼즐을 연 순간부터 정답까지 걸린 시간(초).
  final int seconds;
  final bool isMe;
}

/// 내 순위. `entries` 밖(21위 이하)이어도 서버가 ZRANK 로 따로 보내준다
/// (README "07. 내 순위는 페이지가 아니라 ZRANK 로 따로 읽는다").
@immutable
class MyRank {
  const MyRank({
    required this.rank,
    required this.attempts,
    required this.seconds,
  });

  factory MyRank.fromJson(Map<String, dynamic> json) => MyRank(
    rank: json['rank'] as int,
    attempts: json['attempts'] as int,
    seconds: json['seconds'] as int,
  );

  final int rank;
  final int attempts;
  final int seconds;
}

/// `GET /api/v1/puzzles/today/leaderboard` 응답.
@immutable
class Leaderboard {
  const Leaderboard({
    required this.date,
    required this.language,
    required this.entries,
    this.me,
  });

  factory Leaderboard.fromJson(Map<String, dynamic> json) {
    final me = json['me'] as Map<String, dynamic>?;
    return Leaderboard(
      // 서버가 KST 로 계산한 퍼즐 날짜다.
      date: DateTime.parse(json['date'] as String),
      language:
          PuzzleLanguage.fromWire(json['language'] as String?) ??
          PuzzleLanguage.ko,
      entries: (json['entries'] as List<dynamic>)
          .map(
            (entry) => LeaderboardEntry.fromJson(entry as Map<String, dynamic>),
          )
          .toList(growable: false),
      me: me == null ? null : MyRank.fromJson(me),
    );
  }

  final DateTime date;
  final PuzzleLanguage language;
  final List<LeaderboardEntry> entries;

  /// 아직 못 풀었으면 null.
  final MyRank? me;

  /// 상위 목록에 내 행이 없는가 — 그러면 S3 가 `me` 를 목록 하단에 고정한다.
  bool get isMeOutsideEntries =>
      me != null && !entries.any((entry) => entry.isMe);
}

/// 지난 하루의 결과. `GET /puzzles/today` 의 status 와 값이 겹치지만 한 칸이
/// 다르다 — 지난 날의 시도 0개는 `in_progress` 가 아니라 [none] 이다
/// (README "07. 최근 7일 기록").
enum DayResult {
  success('success'),
  fail('fail'),
  inProgress('in_progress'),
  none('none')
  ;

  const DayResult(this.wire);

  final String wire;

  /// 모르는 값은 미플레이로 떨어뜨린다 — 서버가 결과 종류를 늘려도 그리드는
  /// 칠하지 않은 칸으로 비워 두는 쪽이 틀린 색을 칠하는 것보다 낫다.
  static DayResult fromWire(String? value) {
    for (final result in DayResult.values) {
      if (result.wire == value) return result;
    }
    return none;
  }
}

/// `GET /api/v1/me/history?days=` 의 하루. 서버가 빠진 날 없이 오래된 날짜부터
/// 채워서 보낸다 — 앱은 날짜 계산을 다시 하지 않는다.
@immutable
class HistoryDay {
  const HistoryDay({required this.date, required this.results});

  factory HistoryDay.fromJson(Map<String, dynamic> json) {
    final results = json['results'] as Map<String, dynamic>;
    return HistoryDay(
      date: DateTime.parse(json['date'] as String),
      results: {
        // 앱이 아는 언어만 남긴다 — 서버가 먼저 언어를 늘려도 그릴 칸이 없다.
        for (final language in PuzzleLanguage.values)
          language: DayResult.fromWire(results[language.wire] as String?),
      },
    );
  }

  final DateTime date;
  final Map<PuzzleLanguage, DayResult> results;
}
