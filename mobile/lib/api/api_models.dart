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
