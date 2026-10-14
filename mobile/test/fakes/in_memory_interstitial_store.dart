import 'package:chosung/ads/interstitial_store.dart';

/// shared_preferences 는 플랫폼 채널을 타므로 테스트에서 쓸 수 없다.
/// 생성자의 `puzzleId` 를 미리 채우면 "앱을 다시 켠 뒤" 를 만들 수 있다.
class InMemoryInterstitialStore implements InterstitialStore {
  InMemoryInterstitialStore({int? puzzleId})
    : shown = puzzleId == null ? <int>{} : <int>{puzzleId};

  /// 전면 광고를 띄운 퍼즐들. 테스트가 기록 전체를 직접 본다 — 하나만 남기면
  /// 언어를 왕복할 때 어느 쪽 기록이 밀렸는지 알 수 없다.
  final Set<int> shown;

  @override
  Future<bool> hasShown(int puzzleId) async => shown.contains(puzzleId);

  @override
  Future<void> markShown(int puzzleId) async => shown.add(puzzleId);
}
