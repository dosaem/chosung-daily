import 'package:chosung/subscription/entitlement_schedule.dart';
import 'package:flutter_test/flutter_test.dart';

/// 재확인 타이머의 판정표. 입력 셋(지금·`next_check_at`·포그라운드 여부)에
/// 출력 하나라 표처럼 덮을 수 있다(스펙 Testing "구독 재확인 타이머").
void main() {
  final now = DateTime.utc(2026, 10, 15, 12);

  group('포그라운드', () {
    test('아직 안 됐으면 그 시각에 부른다', () {
      expect(
        nextEntitlementCheck(
          now: now,
          nextCheckAt: now.add(const Duration(hours: 1)),
          foreground: true,
        ),
        now.add(const Duration(hours: 1)),
      );
    });

    // 미정 19: 서버 `is_recheck_due` 도 경계를 포함한다(`now >= 그 시각`).
    // 여기서 "1초 뒤" 를 돌려주면 정각 호출이 재조회를 건너뛴 응답을 받는다.
    test('정확히 그 시각이면 지금 부른다 (경계 포함, 미정 19)', () {
      expect(
        nextEntitlementCheck(now: now, nextCheckAt: now, foreground: true),
        now,
      );
    });

    test('1초 전이면 아직 그 시각을 기다린다', () {
      expect(
        nextEntitlementCheck(
          now: now.subtract(const Duration(seconds: 1)),
          nextCheckAt: now,
          foreground: true,
        ),
        now,
      );
    });

    // 백그라운드에 있던 사이 지나간 경우가 이 길로 들어온다 — 복귀 즉시다.
    test('이미 지났으면 지금 부른다', () {
      expect(
        nextEntitlementCheck(
          now: now,
          nextCheckAt: now.subtract(const Duration(minutes: 30)),
          foreground: true,
        ),
        now,
      );
    });

    test('구독 행이 없는 게스트는 부를 일이 없다', () {
      expect(
        nextEntitlementCheck(now: now, nextCheckAt: null, foreground: true),
        isNull,
      );
    });
  });

  group('백그라운드', () {
    test('타이머를 멈춘다 — 그 시각이 아직 남았어도', () {
      expect(
        nextEntitlementCheck(
          now: now,
          nextCheckAt: now.add(const Duration(minutes: 10)),
          foreground: false,
        ),
        isNull,
      );
    });

    test('타이머를 멈춘다 — 그 시각이 이미 지났어도', () {
      expect(
        nextEntitlementCheck(
          now: now,
          nextCheckAt: now.subtract(const Duration(minutes: 10)),
          foreground: false,
        ),
        isNull,
      );
    });
  });

  // 서버는 UTC 로 보내고(`entitlement.next_check_at`) 기기 시계는 로컬이다.
  // 둘을 그대로 비교해도 되는 건 `isAfter` 가 절대 시각으로 보기 때문이다 —
  // 한쪽을 변환하는 코드가 없는 근거를 여기 둔다.
  group('서버 UTC × 기기 로컬 시계', () {
    test('아직 안 된 UTC 시각은 그대로 돌려준다', () {
      final at = now.add(const Duration(hours: 1));

      expect(
        nextEntitlementCheck(
          now: now.toLocal(),
          nextCheckAt: at,
          foreground: true,
        ),
        at,
      );
    });

    test('지난 UTC 시각이면 기기 시계의 지금이다', () {
      final local = now.toLocal();

      expect(
        nextEntitlementCheck(
          now: local,
          nextCheckAt: now.subtract(const Duration(seconds: 1)),
          foreground: true,
        ),
        local,
      );
    });
  });
}
