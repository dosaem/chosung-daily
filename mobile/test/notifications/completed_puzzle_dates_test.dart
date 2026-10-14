import 'package:chosung/notifications/completed_puzzle_dates.dart';
import 'package:chosung/notifications/notification_plan.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_notifications.dart';

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

  group('시작 read 와 완료 적기의 순서', () {
    /// 시작 read 는 저장소를 타고, 완료 신호는 오늘 API 를 타고 온다 — 두
    /// 결과의 도착 순서는 보장되지 않는다. 늦게 온 시작 read 가 방금 적은
    /// 완료 날짜를 덮어쓰면 **이미 푼 날의 리마인더가 다시 걸린다**(D-30-3).
    test('시작 read 가 늦게 돌아와도 그 사이 적은 완료 날짜가 남는다', () async {
      final store = GatedCompletedPuzzleDateStore();
      final container = ProviderContainer(
        overrides: [completedPuzzleDateStoreProvider.overrideWithValue(store)],
      );
      addTearDown(container.dispose);
      container.listen(completedPuzzleDatesProvider, (_, _) {});

      final todayKey = NotificationPlan.todayKstDate();
      final today = DateTime.parse(todayKey);
      // 시작 read 가 아직 매달려 있는 동안 퍼즐이 끝난다.
      final marked = container
          .read(completedPuzzleDatesProvider.notifier)
          .markCompleted(today);
      await pumpEventQueue();

      // 이제서야 시작 read 가 "아무것도 안 풀었다" 를 들고 돌아온다.
      store.readGate.complete(<String>{});
      await marked;
      await pumpEventQueue();

      expect(container.read(completedPuzzleDatesProvider).value, {todayKey});
      expect(store.dates, {todayKey});
    });
  });
}
