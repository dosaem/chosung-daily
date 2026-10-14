import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// "이 퍼즐에서 전면 광고를 이미 띄웠다" 플래그가 놓이는 자리
/// (`OnboardingStore` 와 같은 방식).
abstract interface class InterstitialStore {
  /// 이 퍼즐에서 전면 광고를 이미 띄웠는가.
  Future<bool> hasShown(int puzzleId);

  Future<void> markShown(int puzzleId);
}

/// 기기 로컬 설정(Android SharedPreferences / iOS NSUserDefaults).
///
/// 서버에 두지 않는 건 광고 노출이 기기에서 일어나는 일이기 때문이다(계정이
/// 같아도 기기마다 센다).
class PreferencesInterstitialStore implements InterstitialStore {
  const PreferencesInterstitialStore(this._preferences);

  /// 값의 타입이 바뀌었으므로(int → 목록) 키도 바꿨다 — 같은 키로 읽으면 이전
  /// 버전이 넣어둔 int 에서 타입 오류가 난다.
  static const _key = 'interstitial_shown_puzzle_ids';

  /// 기억하는 퍼즐 수. **하나로는 모자란다** — 오늘 퍼즐은 언어마다 따로라
  /// (ko·en) 설정에서 언어를 왕복하면 두 퍼즐이 번갈아 "오늘" 이 되고, 하나만
  /// 들고 있으면 바꿀 때마다 이미 띄운 퍼즐에서 다시 뜬다. 지난 퍼즐의 기록은
  /// 쓸 데가 없으니 오래된 쪽부터 밀어낸다(자정이 지나면 새 ID 가 들어온다).
  static const _capacity = 4;

  final SharedPreferencesAsync _preferences;

  @override
  Future<bool> hasShown(int puzzleId) async =>
      (await _shownIds()).contains('$puzzleId');

  @override
  Future<void> markShown(int puzzleId) async {
    final ids = [...await _shownIds(), '$puzzleId'];
    await _preferences.setStringList(
      _key,
      ids.length > _capacity ? ids.sublist(ids.length - _capacity) : ids,
    );
  }

  Future<List<String>> _shownIds() async =>
      await _preferences.getStringList(_key) ?? const [];
}

final interstitialStoreProvider = Provider<InterstitialStore>(
  (ref) => PreferencesInterstitialStore(SharedPreferencesAsync()),
);
