import 'package:chosung/onboarding/onboarding_store.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 이 기기에서 온보딩(S6)을 이미 봤는가. 시작 흐름이 끝난 뒤 홈으로 갈지
/// 온보딩으로 갈지를 가르는 값이다(`startupRedirect`).
///
/// 로딩 중(`AsyncLoading`)에는 아직 아무 데도 보내지 않는다 — 기본값을 false
/// 로 깔고 시작하면 플래그를 읽는 몇 밀리초 동안 **이미 본 사람에게도** 온보딩
/// 첫 장이 번쩍인다.
class OnboardingNotifier extends AsyncNotifier<bool> {
  @override
  Future<bool> build() => ref.read(onboardingStoreProvider).hasSeen();

  /// 온보딩을 끝까지 봤다(또는 건너뛰었다)고 기록한다. 설정의 "하는 법" 으로
  /// 다시 열었을 때도 같은 자리를 지나지만 값은 true 그대로다.
  Future<void> complete() async {
    await ref.read(onboardingStoreProvider).markSeen();
    state = const AsyncData(true);
  }
}

final onboardingSeenProvider = AsyncNotifierProvider<OnboardingNotifier, bool>(
  OnboardingNotifier.new,
);
