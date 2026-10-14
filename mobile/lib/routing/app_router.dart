import 'package:chosung/onboarding/onboarding_controller.dart';
import 'package:chosung/routing/app_routes.dart';
import 'package:chosung/screens/home_shell.dart';
import 'package:chosung/screens/maintenance_screen.dart';
import 'package:chosung/screens/onboarding_screen.dart';
import 'package:chosung/screens/ranking_tab.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/screens/splash_screen.dart';
import 'package:chosung/screens/today_tab.dart';
import 'package:chosung/screens/update_required_screen.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/startup/startup_state.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  // 시작 상태나 온보딩 플래그가 바뀌면 redirect 를 다시 돌린다.
  final refresh = ValueNotifier(0);
  ref
    ..listen(startupProvider, (_, _) => refresh.value++)
    ..listen(onboardingSeenProvider, (_, _) => refresh.value++)
    ..onDispose(refresh.dispose);

  return GoRouter(
    initialLocation: AppRoutes.splash,
    refreshListenable: refresh,
    redirect: (context, state) => startupRedirect(
      ref.read(startupProvider),
      ref.read(onboardingSeenProvider),
      state.matchedLocation,
    ),
    routes: [
      GoRoute(
        path: AppRoutes.splash,
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: AppRoutes.maintenance,
        builder: (context, state) => MaintenanceScreen(
          state:
              _startupStateOf<StartupMaintenance>(ref) ??
              const StartupMaintenance(null),
        ),
      ),
      GoRoute(
        path: AppRoutes.updateRequired,
        builder: (context, state) => UpdateRequiredScreen(
          state:
              _startupStateOf<StartupUpdateRequired>(ref) ??
              const StartupUpdateRequired(null),
        ),
      ),
      GoRoute(
        path: AppRoutes.onboarding,
        builder: (context, state) => const OnboardingScreen(),
      ),
      // 같은 화면을 S4 설정에서 다시 열 때. 경로가 따로 있어야 "끝내면 어디로
      // 가는가"(홈 / 설정)를 화면이 추측하지 않는다.
      GoRoute(
        path: AppRoutes.howTo,
        builder: (context, state) => const OnboardingScreen(isReplay: true),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            HomeShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.today,
                builder: (context, state) => const TodayTab(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.ranking,
                builder: (context, state) => const RankingTab(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.records,
                builder: (context, state) => const RecordsTab(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});

T? _startupStateOf<T extends StartupState>(Ref ref) {
  final state = ref.read(startupProvider).value;
  return state is T ? state : null;
}
