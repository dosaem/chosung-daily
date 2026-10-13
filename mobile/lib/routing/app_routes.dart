import 'package:chosung/startup/startup_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

abstract final class AppRoutes {
  static const splash = '/';
  static const maintenance = '/maintenance';
  static const updateRequired = '/update-required';
  static const today = '/today';
  static const ranking = '/ranking';
  static const records = '/records';

  /// 시작 흐름이 끝나기 전에만 보여주는 화면들.
  static const Set<String> gates = {splash, maintenance, updateRequired};
}

/// 시작 상태만 보고 어디로 보낼지 정한다. go_router 의 `redirect` 가 이걸 쓴다.
///
/// 리다이렉트 루프를 피하려고 "지금 있는 곳이 가야 할 곳이면 null" 규칙을
/// 한 군데에 모았고, 라우터 없이 테스트할 수 있게 순수 함수로 뒀다.
String? startupRedirect(AsyncValue<StartupState> startup, String location) {
  final gate = switch (startup) {
    AsyncData(value: StartupMaintenance()) => AppRoutes.maintenance,
    AsyncData(value: StartupUpdateRequired()) => AppRoutes.updateRequired,
    AsyncData(value: StartupReady()) => null,
    // 로딩·에러는 둘 다 스플래시가 받는다(스켈레톤 / 에러 카드 + 재시도).
    _ => AppRoutes.splash,
  };

  if (gate != null) return location == gate ? null : gate;
  return AppRoutes.gates.contains(location) ? AppRoutes.today : null;
}
