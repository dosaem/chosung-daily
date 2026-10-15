import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// "이 퍼즐의 전면 광고 한 번을 이미 썼다" 예약이 놓이는 자리
/// (`OnboardingStore` 와 같은 방식).
///
/// **"띄웠다" 가 아니라 "예약했다"** 다. 광고를 요청하기 **전에** 적어야
/// "퍼즐당 1회" 가 지켜진다(리뷰 r3 D-31-5) — 표시가 끝난 뒤에 적으면 로드·표시
/// 사이에 창이 생겨 그 사이의 재진입이 또 광고를 띄우고, 광고가 뜬 채로 앱이
/// 죽으면 다시 켤 때 또 뜬다.
abstract interface class InterstitialStore {
  /// 이 퍼즐의 한 번을 이미 썼는가.
  Future<bool> hasReserved(int puzzleId);

  Future<void> reserve(int puzzleId);
}

/// 기억하는 퍼즐 수. **하나로는 모자란다** — 오늘 퍼즐은 언어마다 따로라
/// (ko·en) 설정에서 언어를 왕복하면 두 퍼즐이 번갈아 "오늘" 이 되고, 하나만
/// 들고 있으면 바꿀 때마다 이미 띄운 퍼즐에서 또 뜬다. 지난 퍼즐의 기록은 쓸
/// 데가 없으니(규칙은 오늘 퍼즐에만 걸린다) 오래된 쪽부터 밀어낸다.
const reservedPuzzleIdCapacity = 4;

/// 저장된 예약에 [puzzleId] 를 더한 결과. 같은 ID 는 한 자리만 쓴다 — 중복이
/// 쌓이면 자리를 잡아먹어 다른 언어 퍼즐의 예약이 먼저 밀려난다.
@visibleForTesting
List<String> nextReservedPuzzleIds(List<String> stored, int puzzleId) {
  final ids = [...stored.where((id) => id != '$puzzleId'), '$puzzleId'];
  return ids.length > reservedPuzzleIdCapacity
      ? ids.sublist(ids.length - reservedPuzzleIdCapacity)
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
  /// 이름은 그대로 둔다: 담는 것(퍼즐 ID 목록)과 타입이 같고, 이 티켓은 아직
  /// 출시 전이라 옮길 값이 없다.
  static const _key = 'interstitial_shown_puzzle_ids';

  final SharedPreferencesAsync _preferences;

  @override
  Future<bool> hasReserved(int puzzleId) async =>
      (await _reservedIds()).contains('$puzzleId');

  @override
  Future<void> reserve(int puzzleId) async => _preferences.setStringList(
    _key,
    nextReservedPuzzleIds(await _reservedIds(), puzzleId),
  );

  Future<List<String>> _reservedIds() async =>
      await _preferences.getStringList(_key) ?? const [];
}

final interstitialStoreProvider = Provider<InterstitialStore>(
  (ref) => PreferencesInterstitialStore(SharedPreferencesAsync()),
);
