import 'dart:async';

import 'package:chosung/api/api_models.dart';
import 'package:chosung/config/clock.dart';
import 'package:chosung/records/my_stats_controller.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:chosung/subscription/entitlement_schedule.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 구독 권한을 `/me/stats` 로 다시 맞추는 쪽(스펙 §A.8 재조회 (a), US 30a~30c).
/// 상태는 **지금 걸려 있는 타이머의 발화 시각**이고 null 은 "걸린 타이머 없음"
/// 이다(백그라운드이거나 구독 행이 없는 게스트).
///
/// 부르는 사건은 셋이다 — 앱 시작, 포그라운드 복귀, `next_check_at` 타이머.
/// 그래서 환불·hold 가 확인되면 포그라운드 세션에서 **최대 1시간 + 타이머 오차**
/// 안에 배너 슬롯이 돌아오고 전면 광고가 재개된다(US 30c).
///
/// **조회는 `myStatsProvider` 에 맡긴다.** `/me/stats` 응답 하나에 기록 숫자와
/// 권한이 같이 오므로 여기서 따로 부르면 복귀마다 같은 요청이 두 번 나가고,
/// 계정 경계 검사(`fetchIfSameAccount` — 티켓 29)를 한 벌 더 베껴야 한다.
///
/// **값을 넣는 자리는 31 의 `entitlementProvider` 하나다.** 구매 응답(티켓 32)과
/// 이 경로가 같은 곳을 갱신해야 "구매 직후" 와 "환불 확인 뒤" 가 서로 다른
/// 상태를 보지 않는다.
class EntitlementRefreshController extends Notifier<DateTime?> {
  /// 응답이 알려준 시각에 맞춰 다시 거는 포그라운드 타이머.
  Timer? _timer;

  /// 지금 앱이 보이는가. 시작은 포그라운드다(앱을 켠 사건이 곧 시작이다).
  bool _foreground = true;

  /// 마지막 응답의 `entitlement.next_check_at`.
  DateTime? _nextCheckAt;

  /// 이미 지난 `next_check_at` 을 받았을 때 다음 호출까지 띄우는 간격.
  ///
  /// 서버는 스토어 조회가 실패하면(저장값 유지) 또 다시 물어볼 이유가 없는
  /// 행(expired·revoked)에는 `last_verified_at` 을 올리지 않는다 — 그러면
  /// `next_check_at` 이 계속 과거다. 순수 함수의 "지났으니 지금" 을 그대로
  /// 따르면 응답이 다음 호출을 바로 부르는 고리가 돼 포그라운드 내내
  /// `/me/stats` 를 때린다. 5분은 서버가 만료 ±24h 에 쓰는 재조회 상한과 같은
  /// 값이다(스펙 미정 18) — 그보다 자주 물어도 서버가 스토어를 다시 보지 않는다.
  static const retryGap = Duration(minutes: 5);

  @override
  DateTime? build() {
    // 포그라운드에 머무는 동안만 타이머를 돌린다. 백그라운드에서 멈추지 않으면
    // OS 가 앱을 깨우지 않는 사이 밀린 타이머가 복귀 순간 한꺼번에 터진다.
    //
    // 한 쌍이 아니라 **두 쌍**을 듣는 이유: `AppLifecycleListener` 는 직전
    // 상태를 보고 콜백을 고르고, 이 컨트롤러가 선 직후의 직전 상태는 null 일
    // 수 있다(앱이 아직 한 번도 상태를 안 알린 경우). 그러면 나가는 길에서
    // onHide 와 onPause 중 **하나만** 온다. [_changeVisibility] 가 같은 값을
    // 걸러내므로 둘 다 와도 한 번이다.
    final lifecycle = AppLifecycleListener(
      onShow: () => _changeVisibility(foreground: true),
      onResume: () => _changeVisibility(foreground: true),
      onHide: () => _changeVisibility(foreground: false),
      onPause: () => _changeVisibility(foreground: false),
    );
    ref
      ..onDispose(lifecycle.dispose)
      ..onDispose(_cancelTimer)
      ..listen(myStatsProvider, (_, next) => _adopt(next.value));

    // 시작 응답은 보통 이 컨트롤러가 선 뒤에 온다(스플래시가 `/me/stats` 를
    // 기다린다) — 위 구독이 그걸 받는다. 이미 와 있는 경우에도 같은 길로
    // 반영해 "시작 때 권한을 읽는다" 가 두 사건의 순서에 기대지 않게 한다.
    // 한 틱 미루는 건 Riverpod 이 **build 중에 다른 provider 를 쓰는 것**을
    // 막기 때문이다("Providers are not allowed to modify other providers
    // during their initialization") — 권한을 넣는 자리가 31 의 provider 다.
    if (ref.read(myStatsProvider).value != null) {
      scheduleMicrotask(() {
        if (ref.mounted) _adopt(ref.read(myStatsProvider).value);
      });
    }
    return null;
  }

  /// 지금 떠나 있는 조회가 **언제 떠났는가**. 그 응답을 권한에 넣을 때 이 시각을
  /// 같이 넘겨, 조회가 떠난 뒤 들어온 구매 응답(티켓 32)이 **구매 전** 사실에
  /// 덮이지 않게 한다(`EntitlementNotifier.update` 의 `observedAt`).
  DateTime? _departedAt;

  /// `/me/stats` 를 다시 읽는다. 응답이 오면 [build] 의 구독이 [_adopt] 로 받는다.
  Future<void> refresh() async {
    _departedAt = ref.read(clockProvider)();
    await ref.read(myStatsProvider.notifier).refresh();
    _departedAt = null;
    // 실패한 조회는 `MyStatsNotifier` 가 보던 값을 그대로 둬서 구독이 울리지
    // 않는다(스펙 §A.8 "실패 시 저장값 유지"). 타이머를 다시 거는 자리가
    // 여기에도 있어야 한 번 실패한 세션이 영원히 다시 묻지 않는 일이 없다 —
    // 성공했을 때 한 번 더 거는 건 같은 시각으로 다시 거는 것이라 무해하다.
    if (ref.mounted) state = _arm();
  }

  void _adopt(MyStats? stats) => state = _applied(stats);

  /// 응답 하나를 반영하고 **그래서 걸린 타이머의 발화 시각**을 돌려준다.
  ///
  /// [stats] 가 null 이면 계정 경계를 넘은 것이다(`MyStatsNotifier.discard` —
  /// 연결·전환·삭제). 옛 계정 권한을 들고 있으면 새 계정 화면에서 광고가 빠진
  /// 채로 남고, 그 계정의 `next_check_at` 으로 타이머를 돌릴 이유도 없다.
  DateTime? _applied(MyStats? stats) {
    final entitlement = stats?.entitlement;
    final entitled = ref.read(entitlementProvider.notifier);
    if (entitlement == null) {
      entitled.clear();
    } else {
      // [_departedAt] 이 null 인 응답은 내가 떠나보낸 조회가 아니다(시작 응답,
      // 플레이 결과 뒤 재조회) — 그때는 "지금 관측" 으로 다룬다.
      entitled.update(entitlement, observedAt: _departedAt);
    }

    _nextCheckAt = entitlement?.nextCheckAt;
    return _arm();
  }

  /// 지금 상태(포그라운드 여부 · 마지막 `next_check_at`)로 타이머를 다시 건다.
  DateTime? _arm() {
    _cancelTimer();

    final now = ref.read(clockProvider)();
    final due = nextEntitlementCheck(
      now: now,
      nextCheckAt: _nextCheckAt,
      foreground: _foreground,
    );
    if (due == null) return null;

    // "지났으니 지금"(`due == now`)이 나오는 자리는 방금 `/me/stats` 를 부른
    // 직후다 — 그대로 다시 부르지 않고 [retryGap] 만큼 띄운다.
    final at = due.isAfter(now) ? due : now.add(retryGap);
    _timer = Timer(at.difference(now), () => unawaited(refresh()));
    return at;
  }

  void _changeVisibility({required bool foreground}) {
    if (_foreground == foreground) return;
    _foreground = foreground;

    if (!foreground) {
      state = _arm();
      return;
    }
    // 복귀는 `next_check_at` 을 기다리지 않는다(스펙 §A.8) — 떠나 있던 사이
    // 타이머가 멈춰 있었고, 그동안 환불·hold 가 확인됐을 수 있다.
    unawaited(refresh());
  }

  void _cancelTimer() {
    _timer?.cancel();
    _timer = null;
  }
}

/// 앱이 떠 있는 동안 살아 있어야 한다 — `ChosungApp` 이 구독한다(값은 안 쓰고
/// 수명만 잡아둔다). 화면에 매달면 탭을 옮길 때 타이머가 끊긴다.
final entitlementRefreshProvider =
    NotifierProvider<EntitlementRefreshController, DateTime?>(
      EntitlementRefreshController.new,
    );
