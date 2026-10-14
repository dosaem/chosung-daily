import 'package:chosung/api/api_client.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/guest/guest_token_provider.dart';
import 'package:chosung/startup/startup_plan.dart';
import 'package:chosung/startup/startup_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 앱 시작 흐름: 게스트 토큰 복원·발급 → `/config` → 점검/업데이트/홈 분기.
///
/// 홈으로 갈 때만 `/me/stats` 를 부른다. 그 호출은 토큰이 서버에 아직 살아
/// 있는지 확인하는 역할도 겸해서, 401 이면 게스트를 새로 발급하고 한 번 더
/// 시도한다(그 이상은 재시도하지 않는다 — 두 번째 401 은 서버 문제다).
class StartupNotifier extends AsyncNotifier<StartupState> {
  ApiClient get _api => ref.read(apiClientProvider);

  @override
  Future<StartupState> build() async {
    await _ensureGuestToken();

    final plan = planStartup(
      config: await _api.fetchConfig(),
      appVersion: await ref.read(appVersionProvider.future),
      isIos: ref.read(isIosProvider),
    );

    return switch (plan.destination) {
      StartupDestination.maintenance => StartupMaintenance(
        plan.maintenanceMessage,
      ),
      StartupDestination.updateRequired => StartupUpdateRequired(plan.storeUrl),
      StartupDestination.home => StartupReady(await _fetchStats()),
    };
  }

  /// 재시도 버튼. 처음부터 다시 돌린다.
  void retry() => ref.invalidateSelf();

  Future<void> _ensureGuestToken() async {
    final restored = await ref.read(guestTokenProvider.future);
    if (restored != null && restored.isNotEmpty) return;
    await _issueGuestToken();
  }

  Future<void> _issueGuestToken() async {
    final token = await _api.createGuest(
      puzzleLanguage: ref.read(devicePuzzleLanguageProvider),
    );
    await ref.read(guestTokenProvider.notifier).replaceWith(token);
  }

  Future<MyStats> _fetchStats() async {
    try {
      return await _api.fetchMyStats();
    } on UnauthorizedApiException {
      await ref.read(guestTokenProvider.notifier).clear();
      await _issueGuestToken();
      return _api.fetchMyStats();
    }
  }
}

final startupProvider = AsyncNotifierProvider<StartupNotifier, StartupState>(
  StartupNotifier.new,
);

/// 시작할 때 읽은 내 기록. 아직 준비 상태가 아니면 null(화면은 스켈레톤).
/// 탭들이 자기 데이터를 갖기 전까지(티켓 23·25) 쓰는 통로다.
final startupStatsProvider = Provider<MyStats?>(
  (ref) => switch (ref.watch(startupProvider)) {
    AsyncData(value: StartupReady(:final stats)) => stats,
    _ => null,
  },
);
