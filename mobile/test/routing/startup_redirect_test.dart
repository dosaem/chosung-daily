import 'package:chosung/routing/app_routes.dart';
import 'package:chosung/startup/startup_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';

void main() {
  group('startupRedirect', () {
    test('불러오는 중이면 스플래시로 보낸다', () {
      expect(
        startupRedirect(const AsyncLoading(), AppRoutes.today),
        AppRoutes.splash,
      );
      expect(startupRedirect(const AsyncLoading(), AppRoutes.splash), isNull);
    });

    // 스플래시 화면이 에러 카드 + 재시도 버튼을 띄운다(OVERRIDES §7).
    test('에러면 스플래시에 머문다', () {
      final error = AsyncError<StartupState>(
        Exception('offline'),
        StackTrace.empty,
      );

      expect(startupRedirect(error, AppRoutes.today), AppRoutes.splash);
      expect(startupRedirect(error, AppRoutes.splash), isNull);
    });

    test('점검 중이면 점검 화면으로 보낸다', () {
      const state = AsyncData<StartupState>(StartupMaintenance('안내'));

      expect(startupRedirect(state, AppRoutes.today), AppRoutes.maintenance);
      expect(startupRedirect(state, AppRoutes.maintenance), isNull);
    });

    test('구버전이면 업데이트 화면으로 보낸다', () {
      const state = AsyncData<StartupState>(StartupUpdateRequired(null));

      expect(startupRedirect(state, AppRoutes.today), AppRoutes.updateRequired);
      expect(startupRedirect(state, AppRoutes.updateRequired), isNull);
    });

    test('준비되면 탭 사이 이동은 건드리지 않는다', () {
      final state = AsyncData<StartupState>(StartupReady(fakeMyStats()));

      expect(startupRedirect(state, AppRoutes.today), isNull);
      expect(startupRedirect(state, AppRoutes.ranking), isNull);
      expect(startupRedirect(state, AppRoutes.records), isNull);
    });

    test('준비됐는데 아직 게이트 화면이면 오늘 탭으로 보낸다', () {
      final state = AsyncData<StartupState>(StartupReady(fakeMyStats()));

      expect(startupRedirect(state, AppRoutes.splash), AppRoutes.today);
      expect(startupRedirect(state, AppRoutes.maintenance), AppRoutes.today);
      expect(startupRedirect(state, AppRoutes.updateRequired), AppRoutes.today);
    });
  });
}
