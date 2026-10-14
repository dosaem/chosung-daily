import 'package:chosung/notifications/completed_puzzle_dates.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('퍼즐 날짜 열쇠', () {
    test('서버가 준 퍼즐 날짜를 yyyy-MM-dd 로 적는다', () {
      // `GET /puzzles/today` 의 `date` 는 서버가 KST 로 계산한 퍼즐 날짜다.
      expect(puzzleDateKey(DateTime.parse('2026-10-05')), '2026-10-05');
      expect(puzzleDateKey(DateTime.parse('2026-01-01')), '2026-01-01');
    });
  });

  group('오래된 날짜 정리', () {
    test('KST 오늘보다 이전 날짜는 버린다', () {
      // 완료 집합은 **앞으로의 리마인더를 끄는 데만** 쓰인다 — 지난 날짜는
      // 아무 리마인더와도 안 맞고, 기록의 정본은 서버다.
      expect(
        pruneCompletedDates(const {
          '2026-10-13',
          '2026-10-14',
          '2026-10-15',
          '2026-10-16',
        }, todayKst: '2026-10-15'),
        {'2026-10-15', '2026-10-16'},
      );
    });

    test('버릴 게 없으면 같은 집합이다', () {
      expect(
        pruneCompletedDates(const {'2026-10-15'}, todayKst: '2026-10-15'),
        {'2026-10-15'},
      );
      expect(pruneCompletedDates(const {}, todayKst: '2026-10-15'), isEmpty);
    });
  });
}
