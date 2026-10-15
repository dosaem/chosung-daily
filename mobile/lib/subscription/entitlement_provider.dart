import 'package:chosung/api/api_models.dart';
import 'package:chosung/config/clock.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 지금 이 게스트의 구독 권한 — 서버가 돌려준 [Entitlement] 그대로.
///
/// **null 은 "아직 모른다"** 다 — 시작 직후 `/me/stats`·verify 응답이 오기 전
/// 상태이고, 광고 게이트는 그걸 비구독자로 다룬다(`ad_gate.dart` 참고).
///
/// 이 티켓(31)이 자리를 만들고, 값을 넣는 건 구매(32)와 갱신·타이머(33)다 —
/// 둘이 각자 상태를 들고 있으면 "구매 직후 배너" 와 "권한 만료 뒤 배너" 가
/// 서로 다른 곳을 보게 된다.
///
/// 티켓 32 가 `bool?` 에서 응답 전체로 넓혔다. S4 구독 카드가 "광고 제거 ·
/// 10/31 갱신" 과 "유예 10/20 까지" 를 그려야 하는데(SCREENS S4), 권한 여부와
/// 갱신일을 다른 provider 에 두면 둘이 어긋난 순간이 화면에 남는다.
class EntitlementNotifier extends Notifier<Entitlement?> {
  /// 지금 값이 **언제의 사실**인가(티켓 33). 더 오래된 관측을 걸러내는 데만
  /// 쓴다 — 화면이 읽는 상태는 [Entitlement] 그대로다.
  DateTime? _observedAt;

  @override
  Entitlement? build() => null;

  /// 세터로 두지 않는다 — 호출부(`update(entitlement)`)가 무엇을 바꾸는지
  /// 드러나고, 갱신 시각을 같이 넘길 자리가 된다.
  ///
  /// [observedAt] 은 이 사실을 **관측한 시각**이고, 지금 값의 관측보다 **더
  /// 뒤**여야 이긴다. 재확인 타이머(티켓 33)가 `/me/stats` **조회를 떠난
  /// 시각**을 찍는다 — 조회가 떠난 뒤 구매 응답(티켓 32)이 권한을 넣었는데
  /// 뒤늦게 도착한 **구매 전** 응답이 그걸 덮으면, 돈 낸 사용자가 그 세션
  /// 내내 광고를 본다(그 응답의 `next_check_at` 은 null 이라 다시 물어볼
  /// 타이머도 안 걸린다). 같은 시각이면 이미 들어와 있는 값을 믿는다: 떠난
  /// 시각은 그 응답이 **얼마나 묵었을 수 있는가**의 하한일 뿐이라 동시각을
  /// 이기게 두면 막으려던 그 순서가 그대로 통과한다.
  ///
  /// 생략하면 "지금 관측했다" 로 보고 **늘 이긴다** — 구매·복원(32)처럼 방금
  /// 받은 응답을 그대로 넣는 경로는 시각을 들고 다닐 이유가 없고, 같은 경로가
  /// 잇따라 갱신할 때 기기 시계의 해상도가 둘을 같은 시각으로 만들어 뒤
  /// 갱신을 떨어뜨리는 일도 없어야 한다.
  void update(Entitlement entitlement, {DateTime? observedAt}) {
    if (observedAt == null) {
      _observedAt = ref.read(clockProvider)();
    } else {
      if (_observedAt case final previous? when !observedAt.isAfter(previous)) {
        return;
      }
      _observedAt = observedAt;
    }

    state = entitlement;
  }

  /// 권한을 "아직 모른다" 로 되돌린다(티켓 33). 계정 경계를 넘으면
  /// (연결·전환·삭제) 옛 계정의 권한은 오래된 사본이 아니라 **다른 사람의
  /// 값**이라, 새 계정의 `/me/stats` 가 올 때까지 들고 있으면 그 사이 화면에
  /// 광고가 빠진 채로 남는다.
  ///
  /// 관측 시각도 함께 버린다 — 새 계정의 조회는 옛 계정의 관측보다 먼저
  /// 떠났을 수 있고, 그 비교는 계정이 바뀐 뒤에는 뜻이 없다.
  void clear() {
    _observedAt = null;
    state = null;
  }
}

final entitlementProvider = NotifierProvider<EntitlementNotifier, Entitlement?>(
  EntitlementNotifier.new,
);
