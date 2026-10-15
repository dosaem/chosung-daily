import 'package:chosung/ads/interstitial_store.dart';

/// shared_preferences 는 플랫폼 채널을 타므로 테스트에서 쓸 수 없다.
/// 생성자의 `puzzleId` 를 미리 채우면 "앱을 다시 켠 뒤" 를 만들 수 있다.
class InMemoryInterstitialStore implements InterstitialStore {
  InMemoryInterstitialStore({int? puzzleId})
    : reserved = puzzleId == null ? <int>{} : <int>{puzzleId};

  /// 전면 광고 한 번을 예약한 퍼즐들. 테스트가 예약 전체를 직접 본다 — 하나만
  /// 남기면 언어를 왕복할 때 어느 쪽이 밀렸는지 알 수 없다.
  final Set<int> reserved;

  @override
  Future<bool> hasReserved(int puzzleId) async => reserved.contains(puzzleId);

  @override
  Future<void> reserve(int puzzleId) async => reserved.add(puzzleId);
}
