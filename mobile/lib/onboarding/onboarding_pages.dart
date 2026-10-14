/// S6 온보딩의 장 구성(SCREENS S6).
///
/// 어떤 장이 나오는지는 **플랫폼 하나로만 갈린다** — 그래서 화면을 띄우지
/// 않고도 확인할 수 있게 순수 함수로 뺐다(스펙 §B.20 "판정은 순수 함수").
enum OnboardingPage {
  /// 1장 "하루 한 문제" — 가림 타일 + 언어 칩.
  oneADay,

  /// 2장 "5번의 기회" — 피드백 타일 설명(초록=자리까지 맞음, 회색=아님).
  fiveTries,

  /// 3장 "매일 이어가기" — streak 불꽃 + 알림 권한 사전 안내.
  keepStreak,

  /// 4장(iOS 만) "맞춤 광고 허용" — ATT 사전 안내. 뒤에 시스템 프롬프트가 뜬다.
  tracking
  ;

  /// 퍼즐 언어 칩은 1장 상단에만 둔다(SCREENS S6). 같은 값을 여러 장에서
  /// 바꿀 수 있으면 "마지막에 누른 칩" 이 어디였는지가 장마다 달라진다.
  bool get showsLanguageChips => this == oneADay;
}

/// 이 기기에서 보여줄 장들. iOS 는 맨 뒤에 ATT 안내 1장이 더 붙는다
/// (Android 에는 추적 권한 자체가 없다 — SCREENS S6 "iOS 만").
List<OnboardingPage> onboardingPages({required bool isIos}) => [
  OnboardingPage.oneADay,
  OnboardingPage.fiveTries,
  OnboardingPage.keepStreak,
  if (isIos) OnboardingPage.tracking,
];
