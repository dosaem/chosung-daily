import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// "이 퍼즐에서 전면 광고를 이미 띄웠다" 플래그가 놓이는 자리
/// (`OnboardingStore` 와 같은 방식).
abstract interface class InterstitialStore {
  /// 마지막으로 전면 광고를 띄운 퍼즐. 없으면 null.
  Future<int?> lastShownPuzzleId();

  Future<void> markShown(int puzzleId);
}

/// 기기 로컬 설정(Android SharedPreferences / iOS NSUserDefaults).
///
/// 퍼즐 하나만 기억한다 — "퍼즐당 1회" 는 **오늘 퍼즐**에만 걸리는 규칙이라
/// 지난 퍼즐의 기록을 들고 있을 이유가 없다. 서버에 두지 않는 건 광고 노출이
/// 기기에서 일어나는 일이기 때문이다(계정이 같아도 기기마다 센다).
class PreferencesInterstitialStore implements InterstitialStore {
  const PreferencesInterstitialStore(this._preferences);

  static const _key = 'interstitial_shown_puzzle_id';

  final SharedPreferencesAsync _preferences;

  @override
  Future<int?> lastShownPuzzleId() => _preferences.getInt(_key);

  @override
  Future<void> markShown(int puzzleId) => _preferences.setInt(_key, puzzleId);
}

final interstitialStoreProvider = Provider<InterstitialStore>(
  (ref) => PreferencesInterstitialStore(SharedPreferencesAsync()),
);
