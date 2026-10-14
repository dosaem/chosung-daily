import 'package:chosung/api/api_models.dart';
import 'package:chosung/records/history_grid.dart';
import 'package:flutter_test/flutter_test.dart';

HistoryDay _day(DayResult ko, DayResult en) => HistoryDay(
  date: DateTime(2026, 10, 13),
  results: {PuzzleLanguage.ko: ko, PuzzleLanguage.en: en},
);

void main() {
  group('combinedDayResult', () {
    test('한 언어만 맞춰도 그 날은 성공이다', () {
      expect(
        combinedDayResult(_day(DayResult.success, DayResult.fail)),
        DayResult.success,
      );
      expect(
        combinedDayResult(_day(DayResult.none, DayResult.success)),
        DayResult.success,
      );
    });

    test('아직 끝나지 않은 언어가 있으면 진행 중이다', () {
      expect(
        combinedDayResult(_day(DayResult.fail, DayResult.inProgress)),
        DayResult.inProgress,
      );
    });

    test('푼 언어가 없고 끝난 언어만 있으면 실패다', () {
      expect(
        combinedDayResult(_day(DayResult.fail, DayResult.none)),
        DayResult.fail,
      );
    });

    test('두 언어 다 안 했으면 미플레이다', () {
      expect(
        combinedDayResult(_day(DayResult.none, DayResult.none)),
        DayResult.none,
      );
    });
  });
}
