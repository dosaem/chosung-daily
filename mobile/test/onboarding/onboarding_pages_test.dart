import 'package:chosung/onboarding/onboarding_pages.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('onboardingPages', () {
    test('Android 는 3장이다 — ATT 안내가 없다', () {
      expect(onboardingPages(isIos: false), [
        OnboardingPage.oneADay,
        OnboardingPage.fiveTries,
        OnboardingPage.keepStreak,
      ]);
    });

    test('iOS 는 맨 뒤에 ATT 안내 1장이 더 붙는다', () {
      expect(onboardingPages(isIos: true), [
        OnboardingPage.oneADay,
        OnboardingPage.fiveTries,
        OnboardingPage.keepStreak,
        OnboardingPage.tracking,
      ]);
    });

    test('언어 칩은 1장에만 있다(SCREENS S6)', () {
      expect(OnboardingPage.oneADay.showsLanguageChips, isTrue);
      for (final page in OnboardingPage.values.skip(1)) {
        expect(page.showsLanguageChips, isFalse, reason: '$page');
      }
    });
  });
}
