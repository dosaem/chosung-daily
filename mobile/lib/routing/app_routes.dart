import 'package:chosung/startup/startup_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

abstract final class AppRoutes {
  static const splash = '/';
  static const maintenance = '/maintenance';
  static const updateRequired = '/update-required';

  /// 첫 실행 온보딩(S6). 시작 흐름이 끝나고 플래그가 false 일 때 여기로 보낸다.
  static const onboarding = '/onboarding';

  /// 같은 화면을 S4 설정 "하는 법" 에서 다시 열 때 쓰는 경로. 경로를 나눈
  /// 이유는 **온보딩을 끝내는 방식이 다르기** 때문이다 — 첫 실행은 홈으로
  /// 가고(`go`), 다시 보기는 설정으로 돌아간다(`pop`). 경로가 하나면 "지금
  /// 이게 다시 보기인가" 를 화면이 추측해야 한다.
  static const howTo = '/how-to';

  static const today = '/today';
  static const ranking = '/ranking';
  static const records = '/records';

  /// 시작 흐름이 끝나기 전에만 보여주는 화면들.
  ///
  /// 온보딩은 여기 넣지 않는다 — 넣으면 "다 봤다" 가 되는 순간 다시 보기로
  /// 열어둔 화면까지 홈으로 쫓겨난다.
  static const Set<String> gates = {splash, maintenance, updateRequired};
}

/// 시작 상태와 온보딩 플래그만 보고 어디로 보낼지 정한다. go_router 의
/// `redirect` 가 이걸 쓴다.
///
/// 리다이렉트 루프를 피하려고 "지금 있는 곳이 가야 할 곳이면 null" 규칙을
/// 한 군데에 모았고, 라우터 없이 테스트할 수 있게 순수 함수로 뒀다.
String? startupRedirect(
  AsyncValue<StartupState> startup,
  AsyncValue<bool> onboardingSeen,
  String location,
) {
  final gate = switch (startup) {
    AsyncData(value: StartupMaintenance()) => AppRoutes.maintenance,
    AsyncData(value: StartupUpdateRequired()) => AppRoutes.updateRequired,
    AsyncData(value: StartupReady()) => null,
    // 로딩·에러는 둘 다 스플래시가 받는다(스켈레톤 / 에러 카드 + 재시도).
    _ => AppRoutes.splash,
  };

  if (gate != null) return location == gate ? null : gate;

  final seen = switch (onboardingSeen) {
    AsyncData(:final value) => value,
    // 플래그를 못 읽으면 온보딩에 가두지 않는다 — 읽기가 실패하는 기기는
    // 쓰기도 실패해 매 실행마다 온보딩이 뜬다. 규칙은 설정 "하는 법" 에 있다.
    AsyncError() => true,
    _ => null,
  };
  // 아직 읽는 중: 스플래시에서 기다린다. 기본값을 false 로 깔면 이미 본
  // 사람에게도 온보딩 첫 장이 한 프레임 번쩍인다.
  if (seen == null) {
    return location == AppRoutes.splash ? null : AppRoutes.splash;
  }
  if (!seen) {
    return location == AppRoutes.onboarding ? null : AppRoutes.onboarding;
  }

  return AppRoutes.gates.contains(location) ? AppRoutes.today : null;
}
