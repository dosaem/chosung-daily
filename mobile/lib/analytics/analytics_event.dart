import 'package:chosung/api/api_models.dart';
import 'package:flutter/foundation.dart';

/// 앱이 찍는 분석 이벤트 4개(스펙 §B.24, "미정 항목" 20 에서 확정).
///
/// 이름·파라미터는 Firebase 콘솔에 그대로 나간다 — 한 번 쌓인 이벤트의 이름을
/// 바꾸면 과거 데이터와 끊기므로 여기 한 벌만 두고 구현(Firebase·no-op)은
/// 이 값을 그대로 넘긴다. 만드는 쪽은 순수 함수라 테스트가 직접 본다.
@immutable
class AnalyticsEvent {
  const AnalyticsEvent(this.name, [this.parameters = const {}]);

  final String name;

  /// Firebase 는 값으로 **String·num 만** 받는다(`logEvent` 가 assert 로 막는다).
  final Map<String, Object> parameters;
}

/// 퍼즐이 끝난 순간. [attempts] 는 쓴 시도 수(성공이면 맞춘 회차, 실패면 5).
/// 결과 시트를 다시 열 때는 찍지 않는다 — 한 퍼즐에 한 번이다.
AnalyticsEvent puzzleCompleteEvent({
  required PuzzleLanguage language,
  required bool success,
  required int attempts,
}) => AnalyticsEvent('puzzle_complete', {
  'language': language.wire,
  // bool 을 못 보내므로 1/0 으로 넣는다. Firebase 콘솔에서도 숫자 파라미터는
  // 합·평균을 바로 볼 수 있어 "정답률" 이 그대로 나온다.
  'success': success ? 1 : 0,
  'attempts': attempts,
});

/// 결과를 네이티브 공유 시트로 넘겼다(US 10).
const shareEvent = AnalyticsEvent('share');

/// Paywall(S5)을 봤다. 발화는 티켓 32.
const paywallViewEvent = AnalyticsEvent('paywall_view');

/// 구독 결제를 시작했다. 발화는 티켓 32.
const subscribeStartEvent = AnalyticsEvent('subscribe_start');
