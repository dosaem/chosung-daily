import 'package:chosung/analytics/analytics_event.dart';
import 'package:chosung/api/api_models.dart';
import 'package:flutter_test/flutter_test.dart';

/// 이벤트 이름·파라미터는 Firebase 콘솔에 그대로 나간다 — 바꾸면 과거 데이터와
/// 끊기므로 스펙 "미정 항목" 20 에서 확정한 4개를 테스트가 고정한다.
void main() {
  test('puzzle_complete 는 언어·성공·시도 수를 보낸다', () {
    final event = puzzleCompleteEvent(
      language: PuzzleLanguage.ko,
      success: true,
      attempts: 3,
    );

    expect(event.name, 'puzzle_complete');
    expect(event.parameters, {'language': 'ko', 'success': 1, 'attempts': 3});
  });

  test('실패한 퍼즐의 success 는 0 이다', () {
    final event = puzzleCompleteEvent(
      language: PuzzleLanguage.en,
      success: false,
      attempts: 5,
    );

    expect(event.parameters, {'language': 'en', 'success': 0, 'attempts': 5});
  });

  // Firebase 는 파라미터 값으로 String·num 만 받는다(bool 은 assert 로 막힌다).
  test('파라미터 값은 String 이나 num 뿐이다', () {
    final events = [
      puzzleCompleteEvent(
        language: PuzzleLanguage.ko,
        success: true,
        attempts: 1,
      ),
      shareEvent,
      paywallViewEvent,
      subscribeStartEvent,
    ];

    for (final event in events) {
      for (final value in event.parameters.values) {
        expect(value, anyOf(isA<String>(), isA<num>()), reason: event.name);
      }
    }
  });

  test('나머지 3개는 파라미터 없는 이벤트다', () {
    expect(shareEvent.name, 'share');
    expect(paywallViewEvent.name, 'paywall_view');
    expect(subscribeStartEvent.name, 'subscribe_start');
    expect(shareEvent.parameters, isEmpty);
    expect(paywallViewEvent.parameters, isEmpty);
    expect(subscribeStartEvent.parameters, isEmpty);
  });
}
