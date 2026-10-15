import 'package:chosung/ads/interstitial_store.dart';
import 'package:flutter_test/flutter_test.dart';

/// 저장소에 남는 예약 자체(`SharedPreferencesAsync` 는 플랫폼 채널을 타므로
/// 순수 계산만 본다). 리뷰 r1 D-31-1 이 고친 자리다.
void main() {
  test('처음 예약하면 그 퍼즐만 남는다', () {
    expect(nextReservedPuzzleIds(const [], 41), ['41']);
  });

  // ko·en 두 퍼즐이 같이 "오늘" 일 수 있다 — 둘을 같이 들고 있어야 왕복해도
  // 각각 1회가 된다.
  test('다른 언어 퍼즐을 같이 들고 있는다', () {
    expect(nextReservedPuzzleIds(const ['41'], 42), ['41', '42']);
  });

  test('같은 퍼즐을 다시 예약해도 자리를 하나만 쓴다', () {
    expect(nextReservedPuzzleIds(const ['41', '42'], 41), ['42', '41']);
  });

  test('용량을 넘으면 오래된 예약부터 밀어낸다', () {
    final kept = nextReservedPuzzleIds(const ['38', '39', '40', '41'], 42);

    expect(kept.length, reservedPuzzleIdCapacity);
    expect(kept, ['39', '40', '41', '42']);
    expect(kept, isNot(contains('38')));
  });
}
