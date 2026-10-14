import 'package:chosung/routing/app_routes.dart';
import 'package:chosung/startup/startup_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';

/// "시작은 끝났고 온보딩도 봤다" — 대부분의 기존 분기는 이 상태에서 돈다.
final AsyncValue<StartupState> _ready = AsyncData(StartupReady(fakeMyStats()));
const AsyncValue<bool> _seen = AsyncData(true);
const AsyncValue<bool> _notSeen = AsyncData(false);

void main() {
  group('startupRedirect', () {
    test('불러오는 중이면 스플래시로 보낸다', () {
      expect(
        startupRedirect(const AsyncLoading(), _seen, AppRoutes.today),
        AppRoutes.splash,
      );
      expect(
        startupRedirect(const AsyncLoading(), _seen, AppRoutes.splash),
        isNull,
      );
    });

    // 스플래시 화면이 에러 카드 + 재시도 버튼을 띄운다(OVERRIDES §7).
    test('에러면 스플래시에 머문다', () {
      final error = AsyncError<StartupState>(
        Exception('offline'),
        StackTrace.empty,
      );

      expect(startupRedirect(error, _seen, AppRoutes.today), AppRoutes.splash);
      expect(startupRedirect(error, _seen, AppRoutes.splash), isNull);
    });

    test('점검 중이면 점검 화면으로 보낸다', () {
      const state = AsyncData<StartupState>(StartupMaintenance('안내'));

      expect(
        startupRedirect(state, _seen, AppRoutes.today),
        AppRoutes.maintenance,
      );
      expect(startupRedirect(state, _seen, AppRoutes.maintenance), isNull);
    });

    test('구버전이면 업데이트 화면으로 보낸다', () {
      const state = AsyncData<StartupState>(StartupUpdateRequired(null));

      expect(
        startupRedirect(state, _seen, AppRoutes.today),
        AppRoutes.updateRequired,
      );
      expect(startupRedirect(state, _seen, AppRoutes.updateRequired), isNull);
    });

    test('준비되면 탭 사이 이동은 건드리지 않는다', () {
      expect(startupRedirect(_ready, _seen, AppRoutes.today), isNull);
      expect(startupRedirect(_ready, _seen, AppRoutes.ranking), isNull);
      expect(startupRedirect(_ready, _seen, AppRoutes.records), isNull);
    });

    test('준비됐는데 아직 게이트 화면이면 오늘 탭으로 보낸다', () {
      expect(startupRedirect(_ready, _seen, AppRoutes.splash), AppRoutes.today);
      expect(
        startupRedirect(_ready, _seen, AppRoutes.maintenance),
        AppRoutes.today,
      );
      expect(
        startupRedirect(_ready, _seen, AppRoutes.updateRequired),
        AppRoutes.today,
      );
    });

    group('온보딩(S6)', () {
      test('첫 실행이면 홈 대신 온보딩으로 보낸다', () {
        expect(
          startupRedirect(_ready, _notSeen, AppRoutes.today),
          AppRoutes.onboarding,
        );
        expect(
          startupRedirect(_ready, _notSeen, AppRoutes.splash),
          AppRoutes.onboarding,
        );
        expect(startupRedirect(_ready, _notSeen, AppRoutes.onboarding), isNull);
      });

      // 플래그를 읽는 몇 밀리초 동안 이미 본 사람에게 온보딩이 번쩍이면 안 된다.
      test('플래그를 아직 못 읽었으면 스플래시에서 기다린다', () {
        expect(
          startupRedirect(_ready, const AsyncLoading(), AppRoutes.today),
          AppRoutes.splash,
        );
        expect(
          startupRedirect(_ready, const AsyncLoading(), AppRoutes.splash),
          isNull,
        );
      });

      // 읽기가 실패하면 쓰기도 실패할 가능성이 커서 "매번 온보딩" 이 된다.
      test('플래그 읽기가 실패하면 가두지 않고 홈으로 보낸다', () {
        final failed = AsyncError<bool>(
          Exception('no prefs'),
          StackTrace.empty,
        );

        expect(
          startupRedirect(_ready, failed, AppRoutes.splash),
          AppRoutes.today,
        );
        expect(startupRedirect(_ready, failed, AppRoutes.today), isNull);
      });

      test('점검·업데이트가 온보딩보다 먼저다', () {
        const maintenance = AsyncData<StartupState>(StartupMaintenance(null));

        expect(
          startupRedirect(maintenance, _notSeen, AppRoutes.today),
          AppRoutes.maintenance,
        );
      });

      // 설정 "하는 법" 으로 다시 열었을 때 홈으로 쫓겨나면 안 된다 —
      // 온보딩 경로는 게이트 화면이 아니다.
      test('이미 본 사람이 다시 보기로 들어와도 그 자리에 머문다', () {
        expect(startupRedirect(_ready, _seen, AppRoutes.howTo), isNull);
        expect(startupRedirect(_ready, _seen, AppRoutes.onboarding), isNull);
      });

      test('아직 안 본 사람이 다시 보기 경로로 들어오면 첫 실행 온보딩으로 모은다', () {
        expect(
          startupRedirect(_ready, _notSeen, AppRoutes.howTo),
          AppRoutes.onboarding,
        );
      });
    });
  });
}
