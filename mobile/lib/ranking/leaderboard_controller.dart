import 'package:chosung/api/api_client.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// S3 순위 탭의 상태. 값이 null 이면 "오늘 그 언어의 퍼즐이 아직 없다" 다 —
/// 오류가 아니라 아직이라, 화면은 오류 카드 대신 빈 상태 문구를 보여준다
/// (OVERRIDES §7).
///
/// 퍼즐 언어를 바꾸면 `puzzleLanguageProvider` 가 이 provider 를 무효화한다 —
/// 리더보드는 언어마다 다른 Sorted Set 이다(README "03. 캐시 키는 언어로 갈린다").
class LeaderboardNotifier extends AsyncNotifier<Leaderboard?> {
  ApiClient get _api => ref.read(apiClientProvider);

  @override
  Future<Leaderboard?> build() async {
    try {
      return await _api.fetchTodayLeaderboard();
    } on NoPuzzleTodayApiException {
      return null;
    }
  }

  /// 오류 카드·오프라인 배너의 재시도 버튼.
  void retry() => ref.invalidateSelf();
}

final leaderboardProvider =
    AsyncNotifierProvider<LeaderboardNotifier, Leaderboard?>(
      LeaderboardNotifier.new,
    );
