import 'package:chosung/ads/interstitial_store.dart';

/// shared_preferences 는 플랫폼 채널을 타므로 테스트에서 쓸 수 없다.
/// [puzzleId] 를 미리 채우면 "앱을 다시 켠 뒤" 를 만들 수 있다.
class InMemoryInterstitialStore implements InterstitialStore {
  InMemoryInterstitialStore({this.puzzleId});

  int? puzzleId;

  @override
  Future<int?> lastShownPuzzleId() async => puzzleId;

  @override
  Future<void> markShown(int puzzleId) async => this.puzzleId = puzzleId;
}
