import 'package:chosung/api/api_client.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/guest/account_epoch.dart';
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
    // 순위 자체는 오늘·언어로 갈리는 공용 데이터지만 `me` 표시는 계정 것이다 —
    // 계정이 바뀐 뒤 도착한 응답은 버린다(계정 데이터를 읽는 조회는 모두 같은
    // 장치를 쓴다, D-29-6). 버릴 응답에는 지금 상태를 그대로 돌려줘 `build` 가
    // 돌려준 future 의 쓰기를 무해하게 만든다.
    final loaded = await ref
        .read(accountEpochProvider.notifier)
        .fetchIfSameAccount<Leaderboard?>(() async {
          try {
            return await _api.fetchTodayLeaderboard();
          } on NoPuzzleTodayApiException {
            return null;
          }
        });
    return initialStateOrCurrent<Leaderboard?>(
      loaded,
      () => ref.mounted ? state : const AsyncData<Leaderboard?>(null),
    );
  }

  /// 오류 카드·오프라인 배너의 재시도 버튼.
  void retry() => ref.invalidateSelf();
}

final leaderboardProvider =
    AsyncNotifierProvider<LeaderboardNotifier, Leaderboard?>(
      LeaderboardNotifier.new,
    );
