/// 스토어 스크린샷 5장의 장면(티켓 35, OVERRIDES §8).
///
/// 장면을 integration test 와 **따로** 둔 이유: `flutter drive` 는 시뮬레이터가
/// 있어야 돌아서 CI 가 못 돈다. 장면이 위젯 트리로 떨어져 있으면 같은 장면을
/// `flutter test`(test/store/store_screenshot_scenes_test.dart)가 폰·태블릿 폭
/// 양쪽으로 띄워 보고, 스크린샷을 찍기 전에 "장면이 깨졌다" 를 CI 가 먼저 잡는다.
///
/// 규칙 세 가지:
/// - **라이트 모드 강제**(OVERRIDES §8). 기기 다크 설정과 무관하게 같은 그림이
///   나와야 한다 — `themeMode` 를 고정하고 `darkTheme` 에도 라이트를 넣는다.
/// - **데이터는 `FakeApiClient` 뿐**. 서버 경계만 가짜고 화면·테마·레이아웃은 실제
///   코드다(README "22. 테스트 경계" 와 같은 선).
/// - **배너 슬롯 없음**. 광고 자리는 구독자에게 사라지는 영역이고(OVERRIDES §5),
///   스토어 스크린샷에 빈 회색 띠를 넣을 이유가 없다.
library;

import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/layout/adaptive_scaffold.dart';
import 'package:chosung/screens/onboarding_screen.dart';
import 'package:chosung/screens/ranking_tab.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/screens/today_tab.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../test/fakes/fake_api_client.dart';

/// 찍을 장면. 구독(S5)은 OVERRIDES §8 의 목록에 없어서 빼 둔다.
enum StoreScene {
  /// S1 오늘 — 시도 2행이 쌓인 보드.
  home('01_home'),

  /// S2 결과 — 보드에서 "결과 보기" 를 눌러 띄운 시트/다이얼로그.
  result('02_result'),

  /// S3 순위 — 21위 밖 내 순위까지 보이는 리더보드.
  leaderboard('03_leaderboard'),

  /// S4 내 기록 — 연속 기록 + 최근 7일 + 설정.
  records('04_records'),

  /// S6 온보딩 1장 — 퍼즐 언어를 고르는 칩이 있는 장(언어 선택).
  language('06_language')
  ;

  const StoreScene(this.slug);

  /// 파일 이름에 들어가는 조각. `{locale}_{slug}.png` 로 저장된다.
  final String slug;

  /// 전역 내비게이션이 있는 셸 화면인가. 온보딩은 rail 없이 읽기 폭 가운데로만
  /// 선다(SCREENS T0) — 그래서 폭 ≥600 에서 rail 을 단언하는 대상이 아니다.
  bool get hasShell => this != StoreScene.language;
}

/// 리더보드 표시 이름은 **서버가 만든 문자열을 앱이 그대로 찍는다**
/// (`app/services/puzzle_metrics.py` `display_name`, `ranking_tab.dart`).
/// 지금 서버는 UI 언어와 무관하게 "게스트 #a3f1" 를 주므로, en 스크린샷도 같은
/// 라벨로 찍는다 — 앱이 만들지 않는 화면을 스토어에 올리지 않으려고.
/// (코디네이터 확인 2026-10-15, `review/impl-evidence-35.md` 참고)
const _leaderboardNames = [
  '게스트 #a3f1',
  '게스트 #7b20',
  '게스트 #1c08',
  '게스트 #92de',
  '게스트 #4f61',
];

/// ko "지하철역" — `fakeKoMask` 와 같은 퍼즐이다. 시도 두 줄은 **정답과 앞뒤가
/// 맞는** 피드백이어야 한다: 스토어 스크린샷은 사람이 들여다보는 그림이라,
/// 같은 글자가 한 줄에선 초록이고 다른 줄에선 회색이면 바로 눈에 띈다.
const _koAttempts = [
  PuzzleAttempt(guess: '전화초인', feedback: [false, false, false, false]),
  PuzzleAttempt(guess: '지하철앞', feedback: [true, true, true, false]),
];

/// en "PURPLE" — 모음을 빈칸으로 둔 자음 뼈대(CONTEXT "가림").
const _enMask = [
  MaskTile(type: MaskTileType.revealed, char: 'P'),
  MaskTile(type: MaskTileType.hidden, char: ''),
  MaskTile(type: MaskTileType.revealed, char: 'R'),
  MaskTile(type: MaskTileType.revealed, char: 'P'),
  MaskTile(type: MaskTileType.revealed, char: 'L'),
  MaskTile(type: MaskTileType.hidden, char: ''),
];

const _enAttempts = [
  PuzzleAttempt(
    guess: 'PEOPLE',
    feedback: [true, false, false, true, true, true],
  ),
  PuzzleAttempt(
    guess: 'PIMPLE',
    feedback: [true, false, false, true, true, true],
  ),
];

/// 장면 하나 = 띄울 위젯 + 찍기 전에 할 조작.
class StoreScreenshotScene {
  StoreScreenshotScene({
    required this.scene,
    required this.locale,
    required this.app,
    this.revealLabelKey,
  });

  final StoreScene scene;
  final Locale locale;
  final Widget app;

  /// 장면을 완성하려고 눌러야 하는 버튼의 **번역 키**(결과 시트의 "결과 보기").
  /// 글자가 아니라 키로 들고 있는 이유: `tr()` 은 앱이 떠서 Localization 이
  /// 자리를 잡은 뒤에야 번역을 돌려준다 — 장면을 만들 때 풀면 키가 그대로 남는다.
  final String? revealLabelKey;

  String get fileName => '${locale.languageCode}_${scene.slug}';
}

/// 한 로케일의 5장. 순서가 스토어에 올라가는 순서다.
List<StoreScreenshotScene> storeScreenshotScenes({required Locale locale}) {
  final isKorean = locale.languageCode == 'ko';
  final language = isKorean ? PuzzleLanguage.ko : PuzzleLanguage.en;
  final mask = isKorean ? fakeKoMask : _enMask;
  final attempts = isKorean ? _koAttempts : _enAttempts;
  final answer = isKorean ? '지하철역' : 'PURPLE';

  TodayPuzzle puzzle({required bool finished}) => fakeTodayPuzzle(
    language: language,
    mask: mask,
    attemptsLeft: 3,
    attempts: finished
        ? [
            attempts.first,
            PuzzleAttempt(
              guess: answer,
              feedback: List.filled(
                mask
                    .where((tile) => tile.type != MaskTileType.separator)
                    .length,
                true,
              ),
            ),
          ]
        : attempts,
    status: finished ? PuzzleStatus.success : PuzzleStatus.inProgress,
    answer: finished ? answer : null,
  );

  FakeApiClient api({bool finished = false}) => FakeApiClient(
    config: fakeAppConfig(),
    stats: fakeMyStats(
      puzzleLanguage: language,
      currentStreak: 12,
      maxStreak: 30,
      solvedCount: 41,
    ),
    puzzle: puzzle(finished: finished),
    todayStats: fakeTodayStats(language: language),
    leaderboard: fakeLeaderboard(
      language: language,
      entries: [
        fakeLeaderboardEntry(rank: 1, display: _leaderboardNames[0]),
        fakeLeaderboardEntry(
          rank: 2,
          display: _leaderboardNames[1],
          seconds: 63,
        ),
        fakeLeaderboardEntry(
          rank: 3,
          display: _leaderboardNames[2],
          attempts: 2,
          seconds: 95,
        ),
        fakeLeaderboardEntry(
          rank: 4,
          display: _leaderboardNames[3],
          attempts: 3,
          seconds: 188,
        ),
        fakeLeaderboardEntry(
          rank: 5,
          display: _leaderboardNames[4],
          attempts: 3,
          seconds: 402,
        ),
      ],
      me: const MyRank(rank: 23, attempts: 4, seconds: 754),
    ),
    history: fakeHistory(
      results: [
        for (final result in [
          DayResult.success,
          DayResult.success,
          DayResult.fail,
          DayResult.success,
          DayResult.none,
          DayResult.success,
          DayResult.inProgress,
        ])
          {language: result, _otherLanguage(language): DayResult.none},
      ],
    ),
  );

  return [
    StoreScreenshotScene(
      scene: StoreScene.home,
      locale: locale,
      app: _shell(
        scene: StoreScene.home,
        api: api(),
        locale: locale,
        selectedIndex: 0,
        tab: const TodayTab(),
      ),
    ),
    StoreScreenshotScene(
      scene: StoreScene.result,
      locale: locale,
      app: _shell(
        scene: StoreScene.result,
        api: api(finished: true),
        locale: locale,
        selectedIndex: 0,
        tab: const TodayTab(),
      ),
      revealLabelKey: 'today.show_result',
    ),
    StoreScreenshotScene(
      scene: StoreScene.leaderboard,
      locale: locale,
      app: _shell(
        scene: StoreScene.leaderboard,
        api: api(),
        locale: locale,
        selectedIndex: 1,
        tab: const RankingTab(),
      ),
    ),
    StoreScreenshotScene(
      scene: StoreScene.records,
      locale: locale,
      app: _shell(
        scene: StoreScene.records,
        api: api(),
        locale: locale,
        selectedIndex: 2,
        tab: const RecordsTab(),
      ),
    ),
    StoreScreenshotScene(
      scene: StoreScene.language,
      locale: locale,
      app: _root(
        scene: StoreScene.language,
        api: api(),
        locale: locale,
        home: const OnboardingScreen(),
      ),
    ),
  ];
}

PuzzleLanguage _otherLanguage(PuzzleLanguage language) =>
    language == PuzzleLanguage.ko ? PuzzleLanguage.en : PuzzleLanguage.ko;

/// 탭 셸 — 실제 앱의 `HomeShell` 과 같은 목록·같은 아이콘을 쓴다. 다른 점은
/// go_router 대신 탭을 직접 꽂는 것(스크린샷은 탭 이동을 찍지 않는다)과
/// 배너 슬롯이 없는 것뿐이다.
Widget _shell({
  required StoreScene scene,
  required FakeApiClient api,
  required Locale locale,
  required int selectedIndex,
  required Widget tab,
}) => _root(
  scene: scene,
  api: api,
  locale: locale,
  home: Builder(
    builder: (context) => AdaptiveScaffold(
      selectedIndex: selectedIndex,
      onDestinationSelected: (_) {},
      destinations: [
        AdaptiveDestination(icon: LucideIcons.grid, label: 'tabs.today'.tr()),
        AdaptiveDestination(
          icon: LucideIcons.trophy,
          label: 'tabs.ranking'.tr(),
        ),
        AdaptiveDestination(
          icon: LucideIcons.calendar,
          label: 'tabs.records'.tr(),
        ),
      ],
      body: tab,
    ),
  ),
);

Widget _root({
  required StoreScene scene,
  required FakeApiClient api,
  required Locale locale,
  required Widget home,
}) => ProviderScope(
  // 장면 하나 = provider 그래프 하나. 키가 없으면 장면을 잇따라 띄울 때
  // Flutter 가 같은 Element 를 재사용해서 앞 장면의 응답이 그대로 남는다.
  key: ValueKey(scene),
  retry: noAutoRetry,
  overrides: [
    apiClientProvider.overrideWithValue(api),
    startupStatsProvider.overrideWithValue(api.stats),
    analyticsServiceProvider.overrideWithValue(NoopAnalyticsService()),
    appVersionProvider.overrideWith((ref) async => '1.0.0'),
    // 온보딩 장 수는 플랫폼으로 갈린다 — 스크린샷은 iOS 구성(4장)으로 찍는다.
    isIosProvider.overrideWithValue(true),
  ],
  child: AppLocalizationScope(
    startLocale: locale,
    child: Builder(
      builder: (context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        // 라이트 모드 강제(OVERRIDES §8): darkTheme 에도 라이트를 넣어 둔다 —
        // themeMode 만 고정하면 플랫폼 밝기를 보는 위젯이 남을 수 있다.
        theme: appTheme(Brightness.light),
        darkTheme: appTheme(Brightness.light),
        themeMode: ThemeMode.light,
        locale: context.locale,
        supportedLocales: context.supportedLocales,
        localizationsDelegates: context.localizationDelegates,
        home: home,
      ),
    ),
  ),
);
