import 'package:chosung/onboarding/onboarding_store.dart';

/// shared_preferences 는 플랫폼 채널을 타므로 위젯 테스트에서 쓸 수 없다.
/// 저장소 경계만 메모리로 바꾸고 나머지 흐름은 실제 코드를 그대로 돌린다.
class InMemoryOnboardingStore implements OnboardingStore {
  InMemoryOnboardingStore({this.seen = false});

  bool seen;
  int reads = 0;
  int writes = 0;

  @override
  Future<bool> hasSeen() async {
    reads++;
    return seen;
  }

  @override
  Future<void> markSeen() async {
    seen = true;
    writes++;
  }
}
