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

/// 테스트용 [ApiClient]. 서버가 돌려줄 값을 그대로 들고 있고, 호출 횟수와
/// 보낸 인자를 기록한다. 응답을 바꾸려면 필드를 다시 넣으면 된다.
class FakeApiClient implements ApiClient {
  FakeApiClient({
    AppConfig? config,
    MyStats? stats,
    this.nextGuestToken = 'fake-guest-token',
  }) : config = config ?? fakeAppConfig(),
       stats = stats ?? fakeMyStats();

  AppConfig config;
  MyStats stats;
  String nextGuestToken;

  /// 넣어두면 그 호출이 이 예외를 던진다.
  Exception? createGuestError;
  Exception? fetchConfigError;
  Exception? fetchMyStatsError;

  final List<PuzzleLanguage> createGuestLanguages = [];
  int fetchConfigCalls = 0;
  int fetchMyStatsCalls = 0;

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
}
