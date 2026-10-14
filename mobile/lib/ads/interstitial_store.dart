import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// "이 퍼즐에서 전면 광고를 이미 띄웠다" 플래그가 놓이는 자리
/// (`OnboardingStore` 와 같은 방식).
abstract interface class InterstitialStore {
  /// 이 퍼즐에서 전면 광고를 이미 띄웠는가.
  Future<bool> hasShown(int puzzleId);

  Future<void> markShown(int puzzleId);
}

/// 기억하는 퍼즐 수. **하나로는 모자란다** — 오늘 퍼즐은 언어마다 따로라
/// (ko·en) 설정에서 언어를 왕복하면 두 퍼즐이 번갈아 "오늘" 이 되고, 하나만
/// 들고 있으면 바꿀 때마다 이미 띄운 퍼즐에서 또 뜬다. 지난 퍼즐의 기록은 쓸
/// 데가 없으니(규칙은 오늘 퍼즐에만 걸린다) 오래된 쪽부터 밀어낸다.
const shownPuzzleIdCapacity = 4;

/// 저장된 기록에 [puzzleId] 를 더한 결과. 같은 ID 는 한 자리만 쓴다 — 중복이
/// 쌓이면 자리를 잡아먹어 다른 언어 퍼즐의 기록이 먼저 밀려난다.
@visibleForTesting
List<String> nextShownPuzzleIds(List<String> stored, int puzzleId) {
  final ids = [...stored.where((id) => id != '$puzzleId'), '$puzzleId'];
  return ids.length > shownPuzzleIdCapacity
      ? ids.sublist(ids.length - shownPuzzleIdCapacity)
      : ids;
}

/// 기기 로컬 설정(Android SharedPreferences / iOS NSUserDefaults).
///
/// 서버에 두지 않는 건 광고 노출이 기기에서 일어나는 일이기 때문이다(계정이
/// 같아도 기기마다 센다).
class PreferencesInterstitialStore implements InterstitialStore {
  const PreferencesInterstitialStore(this._preferences);

  /// 값이 int 하나에서 목록으로 바뀌었으므로 키도 새로 썼다 — 같은 키로
  /// `getStringList` 를 부르면 이전 버전이 넣어둔 int 에서 타입 오류가 난다.
  static const _key = 'interstitial_shown_puzzle_ids';

  final SharedPreferencesAsync _preferences;

  @override
  Future<bool> hasShown(int puzzleId) async =>
      (await _shownIds()).contains('$puzzleId');

  @override
  Future<void> markShown(int puzzleId) async => _preferences.setStringList(
    _key,
    nextShownPuzzleIds(await _shownIds(), puzzleId),
  );

  Future<List<String>> _shownIds() async =>
      await _preferences.getStringList(_key) ?? const [];
}

final interstitialStoreProvider = Provider<InterstitialStore>(
  (ref) => PreferencesInterstitialStore(SharedPreferencesAsync()),
);
