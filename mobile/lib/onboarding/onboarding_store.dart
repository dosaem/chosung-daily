import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// "이 기기에서 온보딩을 봤다" 플래그가 놓이는 자리. 플랫폼 채널을 타는
/// 구현을 테스트에서 메모리로 바꿔 끼우려고 인터페이스를 뒀다
/// (`GuestTokenStore` 와 같은 방식).
abstract interface class OnboardingStore {
  Future<bool> hasSeen();
  Future<void> markSeen();
}

/// 기기 로컬 설정(Android SharedPreferences / iOS NSUserDefaults).
///
/// 게스트 토큰과 달리 Keychain 을 쓰지 않는다 — 비밀이 아니고, 무엇보다
/// iOS Keychain 은 앱을 지워도 남아서 "지웠다 다시 깐 사람" 이 온보딩을 다시
/// 못 보게 된다. 서버에 두지 않는 건 "기기마다 한 번" 이 이 플래그의 뜻이기
/// 때문이다(같은 계정이라도 새 기기에서는 다시 본다).
class PreferencesOnboardingStore implements OnboardingStore {
  const PreferencesOnboardingStore(this._preferences);

  static const _key = 'onboarding_seen';

  final SharedPreferencesAsync _preferences;

  @override
  Future<bool> hasSeen() async => await _preferences.getBool(_key) ?? false;

  @override
  Future<void> markSeen() => _preferences.setBool(_key, true);
}

final onboardingStoreProvider = Provider<OnboardingStore>(
  (ref) => PreferencesOnboardingStore(SharedPreferencesAsync()),
);
