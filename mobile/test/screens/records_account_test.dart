import 'dart:async';

import 'package:chosung/account/social_sign_in.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/layout/adaptive_sheet.dart';
import 'package:chosung/local/local_flags.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/settings/legal_links.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/account_card.dart';
import 'package:chosung/widgets/backup_code_sheet.dart';
import 'package:chosung/widgets/delete_account_dialog.dart';
import 'package:chosung/widgets/seven_day_grid.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/in_memory_guest_token_store.dart';
import '../fakes/in_memory_local_flag_store.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 티켓 29 가 채운 S4 계정 자리를 실제 화면에서 돌린다. 서버(`ApiClient`)와
/// 네이티브 로그인·저장소만 가짜고, 나머지(컨트롤러·토큰 교체·재조회)는
/// 앱 코드 그대로다.
class _Harness {
  _Harness({
    required this.api,
    required this.store,
    required this.flags,
    required this.signInCalls,
  });

  final FakeApiClient api;
  final InMemoryGuestTokenStore store;
  final InMemoryLocalFlagStore flags;
  final List<AccountProvider> signInCalls;
}

Future<_Harness> _pump(
  WidgetTester tester, {
  FakeApiClient? client,
  MyStats? startup,
  SocialCredential? credential,
  bool isIos = true,
  String token = 'guest-token',
  Size size = const Size(390, 844),
  Locale locale = const Locale('ko'),
}) async {
  final api = client ?? FakeApiClient();
  final store = InMemoryGuestTokenStore(token);
  final flags = InMemoryLocalFlagStore();
  final signInCalls = <AccountProvider>[];

  setViewSize(tester, size);
  await tester.runAsync(() async {
    await tester.pumpWidget(
      ProviderScope(
        retry: noAutoRetry,
        overrides: [
          apiClientProvider.overrideWithValue(api),
          guestTokenStoreProvider.overrideWithValue(store),
          localFlagStoreProvider.overrideWithValue(flags),
          isIosProvider.overrideWithValue(isIos),
          startupStatsProvider.overrideWithValue(startup ?? fakeMyStats()),
          appVersionProvider.overrideWith((ref) async => '1.2.3'),
          webLinkLauncherProvider.overrideWithValue((_) async {}),
          socialSignInProvider.overrideWithValue((provider) async {
            signInCalls.add(provider);
            return credential ??
                SocialCredential(
                  provider: provider,
                  idToken: '${provider.wire}-id-token',
                  authorizationCode: provider == AccountProvider.apple
                      ? 'apple-auth-code'
                      : null,
                );
          }),
        ],
        child: AppLocalizationScope(
          startLocale: locale,
          child: Builder(
            builder: (context) => MaterialApp(
              theme: appTheme(Brightness.light),
              locale: context.locale,
              supportedLocales: context.supportedLocales,
              localizationsDelegates: context.localizationDelegates,
              home: const Scaffold(
                body: Column(
                  children: [
                    // 홈 탭은 셸에서 계속 살아 있다 — 전환 뒤 보드를 다시
                    // 읽는지 보려면 떠 있어야 한다.
                    SizedBox(height: 0, child: _LiveHomeTab()),
                    Expanded(child: RecordsTab()),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
  });
  await tester.pumpAndSettle();

  return _Harness(
    api: api,
    store: store,
    flags: flags,
    signInCalls: signInCalls,
  );
}

class _LiveHomeTab extends ConsumerWidget {
  const _LiveHomeTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(todayPuzzleProvider);
    return const SizedBox.shrink();
  }
}

/// 가짜 ApiClient 의 Future 는 실제 이벤트 루프에서 끝난다 — 탭 뒤에도
/// `runAsync` 가 필요하다. 삭제 버튼은 1열에서 화면 밖이라 먼저 스크롤한다.
Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.runAsync(() async {
    await tester.tap(finder);
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

void main() {
  // todayPuzzleProvider 가 AppLifecycleListener 를 만든다.
  TestWidgetsFlutterBinding.ensureInitialized();

  group('AccountCard', () {
    testWidgets('iOS 는 구글·애플 두 버튼이다', (tester) async {
      await _pump(tester);

      expect(find.byKey(accountLinkGoogleKey), findsOneWidget);
      expect(find.byKey(accountLinkAppleKey), findsOneWidget);
      expect(find.text('어느 기기에서든 같은 기록'), findsOneWidget);
    });

    testWidgets('Android 는 구글만이다 — 애플 로그인이 없다', (tester) async {
      await _pump(tester, isIos: false);

      expect(find.byKey(accountLinkGoogleKey), findsOneWidget);
      expect(find.byKey(accountLinkAppleKey), findsNothing);
    });

    testWidgets('연결됐으면 provider 와 마스킹 이메일을 보여준다', (tester) async {
      await _pump(
        tester,
        startup: fakeMyStats(
          linkedAccount: const LinkedAccount(
            provider: 'google',
            email: 'hsseo@gmail.com',
          ),
        ),
      );

      expect(find.text('Google · hs***@gmail.com 연결됨'), findsOneWidget);
      expect(find.byKey(accountLinkGoogleKey), findsNothing);
    });

    testWidgets('연결됨 Google 은 중립 아이콘과 텍스트 라벨로 가른다', (tester) async {
      // D-29-3: 티켓 체크박스 3·SCREENS S4 는 provider 를 알아볼 수 있기를
      // 요구한다. Apple 은 Lucide 의 apple 마크로 가르고, Google 은 대응하는
      // 마크가 없어 중립 아이콘 + "Google" 텍스트 라벨로 가른다 — 브라우저
      // 브랜드인 chrome 을 쓰면 다른 제품으로 읽힌다(README 설계 판단 29).
      await _pump(
        tester,
        startup: fakeMyStats(
          linkedAccount: const LinkedAccount(
            provider: 'google',
            email: 'hsseo@gmail.com',
          ),
        ),
      );

      expect(find.byIcon(LucideIcons.userCheck), findsOneWidget);
      expect(find.byIcon(LucideIcons.apple), findsNothing);
      // 브라우저 브랜드 마크를 구글 계정 자리에 두지 않는다.
      expect(find.byIcon(LucideIcons.chrome), findsNothing);
      expect(find.text('Google · hs***@gmail.com 연결됨'), findsOneWidget);
    });

    testWidgets('연결됨 아이콘은 Apple 이면 apple 이다', (tester) async {
      await _pump(
        tester,
        startup: fakeMyStats(
          linkedAccount: const LinkedAccount(provider: 'apple'),
        ),
      );

      expect(find.byIcon(LucideIcons.apple), findsOneWidget);
      expect(find.byIcon(LucideIcons.userCheck), findsNothing);
    });

    testWidgets('모르는 provider 면 공통 아이콘으로 떨어진다', (tester) async {
      await _pump(
        tester,
        startup: fakeMyStats(
          linkedAccount: const LinkedAccount(provider: 'kakao'),
        ),
      );

      expect(find.byIcon(LucideIcons.userCheck), findsOneWidget);
    });

    testWidgets('구글 연결에 성공하면 전환 안내와 함께 기록을 다시 읽는다', (tester) async {
      final api = FakeApiClient(
        stats: fakeMyStats(
          currentStreak: 42,
          linkedAccount: const LinkedAccount(
            provider: 'google',
            email: 'hsseo@gmail.com',
          ),
        ),
        nextLinkedToken: 'other-device-token',
      );
      final world = await _pump(tester, client: api);
      final puzzleCalls = api.fetchTodayPuzzleCalls;
      final historyCalls = api.fetchMyHistoryDays.length;

      await _tap(tester, find.byKey(accountLinkGoogleKey));

      expect(world.signInCalls, [AccountProvider.google]);
      expect(api.exchangedCredentials.single.idToken, 'google-id-token');
      expect(world.store.token, 'other-device-token');
      // 화면: 연결됨 + 전환 안내. 숫자도 새 계정 것으로 바뀐다.
      expect(find.text('Google · hs***@gmail.com 연결됨'), findsOneWidget);
      expect(find.text('이 계정의 기록으로 전환됐어요'), findsOneWidget);
      expect(find.text('42일'), findsOneWidget);
      // 로컬 상태 폐기: 보드와 7일 그리드를 새 토큰으로 다시 읽는다.
      expect(api.fetchTodayPuzzleCalls, puzzleCalls + 1);
      expect(api.fetchMyHistoryDays.length, historyCalls + 1);
    });

    testWidgets('전환 뒤 기록을 못 읽으면 옛 기록이 사라지고 오류가 뜬다', (tester) async {
      // D-29-1 을 화면에서 본다: 토큰은 B 인데 화면이 A 를 보여주면, 그 화면
      // 아래 삭제 버튼이 A 가 아니라 B 를 지운다.
      final api = FakeApiClient(nextLinkedToken: 'other-device-token')
        ..fetchMyStatsError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );
      final world = await _pump(
        tester,
        client: api,
        startup: fakeMyStats(currentStreak: 99),
      );
      expect(find.text('99일'), findsOneWidget);

      await _tap(tester, find.byKey(accountLinkGoogleKey));

      expect(world.store.token, 'other-device-token');
      expect(find.text('99일'), findsNothing);
      expect(find.text('네트워크에 연결할 수 없어요'), findsOneWidget);
    });

    testWidgets('애플 연결은 authorization_code 를 같이 보낸다', (tester) async {
      final world = await _pump(tester);

      await _tap(tester, find.byKey(accountLinkAppleKey));

      expect(world.signInCalls, [AccountProvider.apple]);
      expect(
        world.api.exchangedCredentials.single.authorizationCode,
        'apple-auth-code',
      );
    });

    testWidgets('이미 연결된 계정이면 그 문구를 카드 아래 한 줄로 둔다', (tester) async {
      final api = FakeApiClient()
        ..exchangeIdTokenError = const AccountAlreadyLinkedApiException(
          code: 'ACCOUNT_ALREADY_LINKED',
          message: '',
        );
      final world = await _pump(tester, client: api);

      await _tap(tester, find.byKey(accountLinkGoogleKey));

      expect(find.text('이미 다른 계정이 연결돼 있어요'), findsOneWidget);
      expect(world.store.token, 'guest-token');
    });

    testWidgets('id_token 을 확인 못 하면 로그인 확인 문구다', (tester) async {
      final api = FakeApiClient()
        ..exchangeIdTokenError = const InvalidIdTokenApiException(
          code: 'INVALID_ID_TOKEN',
          message: '',
        );
      await _pump(tester, client: api);

      await _tap(tester, find.byKey(accountLinkGoogleKey));

      expect(find.text('로그인을 확인하지 못했어요. 다시 시도해주세요'), findsOneWidget);
    });
  });

  group('백업 코드 시트', () {
    testWidgets('유효한 코드면 토큰을 갈아끼우고 시트가 닫힌다', (tester) async {
      final api = FakeApiClient()
        ..statsByToken['backup-code'] = fakeMyStats(currentStreak: 7);
      final world = await _pump(tester, client: api);

      await _tap(tester, find.text('다른 기기 기록 불러오기'));
      expect(find.byType(BackupCodeSheet), findsOneWidget);

      await tester.enterText(find.byKey(backupCodeFieldKey), 'backup-code');
      await tester.pumpAndSettle();
      await _tap(tester, find.byKey(backupCodeSubmitKey));

      expect(find.byType(BackupCodeSheet), findsNothing);
      expect(world.store.token, 'backup-code');
      expect(api.statsTokens, ['backup-code']);
    });

    testWidgets('전환하면 카드가 바로 새 계정을 보여준다', (tester) async {
      // D-29-1 의 원래 재현: A 가 연결된 화면에서 B 의 코드를 넣는다. 코드
      // 확인이 이미 B 의 `/me/stats` 를 받아 왔으므로, 그 뒤 재조회가
      // 실패해도(여기서는 아예 실패시킨다) 카드에 A 가 남으면 안 된다.
      final api = FakeApiClient()
        ..statsByToken['backup-code'] = fakeMyStats(
          currentStreak: 7,
          linkedAccount: const LinkedAccount(
            provider: 'google',
            email: 'b@gmail.com',
          ),
        )
        ..fetchMyStatsError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );
      final world = await _pump(
        tester,
        client: api,
        startup: fakeMyStats(
          currentStreak: 99,
          linkedAccount: const LinkedAccount(
            provider: 'apple',
            email: 'a@icloud.com',
          ),
        ),
      );

      await _tap(tester, find.text('다른 기기 기록 불러오기'));
      await tester.enterText(find.byKey(backupCodeFieldKey), 'backup-code');
      await tester.pumpAndSettle();
      await _tap(tester, find.byKey(backupCodeSubmitKey));

      expect(world.store.token, 'backup-code');
      expect(find.text('Apple · a***@icloud.com 연결됨'), findsNothing);
      expect(find.text('Google · b***@gmail.com 연결됨'), findsOneWidget);
      expect(find.text('7일'), findsOneWidget);
    });

    testWidgets('전환하면 7일 칸이 비워지고 새 계정 칸이 들어온다', (tester) async {
      // 읽기 전용 표시지만 계정이 바뀌면 **다른 사람의 7일**이다. 무효화로는
      // 비워지지 않아(`copyWithPrevious`) 이 화면이 옛 계정 칸을 계속 골랐다.
      final api = FakeApiClient()
        ..statsByToken['backup-code'] = fakeMyStats(currentStreak: 4);
      final world = await _pump(tester, client: api);
      expect(find.byType(SevenDayGrid), findsOneWidget);

      // B 의 7일 조회만 붙잡는다 — 전환은 끝났고 칸만 아직 안 왔다.
      final gate = Completer<void>();
      api.fetchMyHistoryGate = gate;
      addTearDown(() {
        if (!gate.isCompleted) gate.complete();
      });

      await _tap(tester, find.text('다른 기기 기록 불러오기'));
      await tester.enterText(find.byKey(backupCodeFieldKey), 'backup-code');
      await tester.pumpAndSettle();
      await _tap(tester, find.byKey(backupCodeSubmitKey));

      expect(world.store.token, 'backup-code');
      expect(
        find.byType(SevenDayGrid),
        findsNothing,
        reason: '옛 계정의 7일 칸이 남았다',
      );

      // B 의 칸이 도착하면 그 자리를 받는다.
      api.fetchMyHistoryGate = null;
      await tester.runAsync(() async {
        gate.complete();
        await pumpEventQueue();
        await tester.pump();
      });
      await tester.pumpAndSettle();
      expect(find.byType(SevenDayGrid), findsOneWidget);
    });

    testWidgets('틀린 코드면 시트가 열린 채로 오류를 보여준다', (tester) async {
      final world = await _pump(tester);

      await _tap(tester, find.text('다른 기기 기록 불러오기'));
      await tester.enterText(find.byKey(backupCodeFieldKey), 'nope');
      await tester.pumpAndSettle();
      await _tap(tester, find.byKey(backupCodeSubmitKey));

      expect(find.byType(BackupCodeSheet), findsOneWidget);
      expect(find.text('올바르지 않은 백업 코드'), findsOneWidget);
      expect(world.store.token, 'guest-token');
    });

    testWidgets('빈 코드로는 보낼 수 없다', (tester) async {
      final world = await _pump(tester);

      await _tap(tester, find.text('다른 기기 기록 불러오기'));

      final submit = tester.widget<FilledButton>(
        find.byKey(backupCodeSubmitKey),
      );
      expect(submit.onPressed, isNull);
      expect(world.api.statsTokens, isEmpty);
    });
  });

  group('계정 삭제', () {
    // 기기 식별자 문장은 방침 `#automatic-collection`·`#destruction` 과 같은 말을
    // 한다(티켓 47) — 앱은 삭제 뒤 **새 토큰을 받아 덮어쓰므로** 재설치로 지운
    // 기록이 돌아오지 않는다. 문구가 빠지면 방침만 그 사실을 말하는 상태가 된다.
    testWidgets('다이얼로그에 되돌릴 수 없음·기기 식별자 교체·구독 별도 해지가 적혀 있다', (
      tester,
    ) async {
      await _pump(tester);

      await _tap(tester, find.byKey(RecordsSlot.deleteAccount));

      expect(find.byType(DeleteAccountConfirm), findsOneWidget);
      expect(
        find.text(
          '기록·계정이 전부 삭제되고 되돌릴 수 없어요. '
          '이 기기에 저장된 식별자도 새 값으로 바뀌어서, 앱을 지웠다 다시 깔아도 '
          '이 기록으로 돌아올 수 없어요. '
          '구독 중이면 App Store/Google Play 에서 따로 해지해야 해요.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('취소하면 아무것도 지우지 않는다', (tester) async {
      final world = await _pump(tester);

      await _tap(tester, find.byKey(RecordsSlot.deleteAccount));
      await _tap(tester, find.byKey(deleteAccountCancelKey));

      expect(world.api.deleteAccountCalls, 0);
      expect(world.store.token, 'guest-token');
    });

    testWidgets('삭제하면 DELETE /me 뒤 새 게스트로 돌아간다', (tester) async {
      final api = FakeApiClient(
        nextGuestToken: 'fresh-guest',
        stats: fakeMyStats(),
      );
      final world = await _pump(tester, client: api);
      await world.flags.set(LocalFlag.linkAccountNoticeSeen);

      await _tap(tester, find.byKey(RecordsSlot.deleteAccount));
      await _tap(tester, find.byKey(deleteAccountConfirmKey));

      expect(api.deleteAccountCalls, 1);
      expect(api.createGuestCalls, 1);
      expect(world.store.token, 'fresh-guest');
      expect(await world.flags.isSet(LocalFlag.linkAccountNoticeSeen), isFalse);
      expect(find.text('계정을 삭제하고 새로 시작했어요'), findsOneWidget);
      // 새 게스트라 계정 연결 버튼이 다시 보인다.
      expect(find.byKey(accountLinkGoogleKey), findsOneWidget);
    });

    testWidgets('게스트 발급이 실패했다가 돌아오면 다시 눌러 복구한다', (tester) async {
      // D-29-2 를 화면에서 본다: `DELETE /me` 는 성공했고 `POST /guests` 만
      // 실패했다. 서버 계정은 이미 사라졌으니 재시도가 DELETE 부터 다시 돌면
      // 401 로 끝나고 앱은 죽은 토큰에 갇힌다.
      final api = FakeApiClient(nextGuestToken: 'fresh-guest')
        ..createGuestError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );
      final world = await _pump(
        tester,
        client: api,
        startup: fakeMyStats(
          currentStreak: 99,
          linkedAccount: const LinkedAccount(
            provider: 'google',
            email: 'a@gmail.com',
          ),
        ),
      );
      await world.flags.set(LocalFlag.linkAccountNoticeSeen);

      await _tap(tester, find.byKey(RecordsSlot.deleteAccount));
      await _tap(tester, find.byKey(deleteAccountConfirmKey));

      expect(find.text('네트워크에 연결할 수 없어요'), findsOneWidget);
      // 지워진 계정의 이름·기록이 화면에 남아 있으면 안 된다.
      expect(find.text('Google · a***@gmail.com 연결됨'), findsNothing);
      expect(find.text('99일'), findsNothing);

      api
        ..createGuestError = null
        ..deleteAccountError = const UnauthorizedApiException(
          code: 'UNAUTHORIZED',
          message: '게스트를 찾을 수 없습니다.',
        );

      await _tap(tester, find.byKey(RecordsSlot.deleteAccount));
      await _tap(tester, find.byKey(deleteAccountConfirmKey));

      expect(api.deleteAccountCalls, 1);
      expect(api.createGuestCalls, 2);
      expect(world.store.token, 'fresh-guest');
      expect(await world.flags.isSet(LocalFlag.linkAccountNoticeSeen), isFalse);
      expect(find.text('계정을 삭제하고 새로 시작했어요'), findsOneWidget);
    });

    testWidgets('발급 실패 뒤 다른 계정을 불러오면 그 계정을 지운다', (tester) async {
      // D-29-4 를 화면에서 본다: A 삭제 성공 → 발급 실패 → 백업 코드로 B 전환
      // → 다시 삭제. 마지막 삭제가 B 의 `DELETE /me` 를 생략하면 서버에 B 가
      // 남은 채로 "삭제하고 새로 시작했어요" 가 뜬다 — 사용자의 삭제 요구가
      // 이행되지 않는다.
      final api = FakeApiClient(nextGuestToken: 'fresh-guest')
        ..statsByToken['b-backup-code'] = fakeMyStats(
          currentStreak: 7,
          linkedAccount: const LinkedAccount(
            provider: 'google',
            email: 'b@gmail.com',
          ),
        )
        ..createGuestError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );
      final world = await _pump(
        tester,
        client: api,
        startup: fakeMyStats(
          linkedAccount: const LinkedAccount(
            provider: 'apple',
            email: 'a@icloud.com',
          ),
        ),
      );

      await _tap(tester, find.byKey(RecordsSlot.deleteAccount));
      await _tap(tester, find.byKey(deleteAccountConfirmKey));
      expect(api.deleteAccountCalls, 1);
      expect(find.text('네트워크에 연결할 수 없어요'), findsOneWidget);

      api.createGuestError = null;
      await _tap(tester, find.text('다른 기기 기록 불러오기'));
      await tester.enterText(find.byKey(backupCodeFieldKey), 'b-backup-code');
      await tester.pumpAndSettle();
      await _tap(tester, find.byKey(backupCodeSubmitKey));

      expect(world.store.token, 'b-backup-code');
      expect(find.text('Google · b***@gmail.com 연결됨'), findsOneWidget);

      await _tap(tester, find.byKey(RecordsSlot.deleteAccount));
      await _tap(tester, find.byKey(deleteAccountConfirmKey));

      expect(find.text('계정을 삭제하고 새로 시작했어요'), findsOneWidget);
      expect(api.deleteAccountCalls, 2);
      expect(world.store.token, 'fresh-guest');
    });
  });

  group('태블릿(T2)', () {
    testWidgets('폭 744 에서는 백업 코드 시트와 삭제 다이얼로그가 다이얼로그로 뜬다', (tester) async {
      await _pump(tester, size: const Size(744, 1133));

      await _tap(tester, find.text('다른 기기 기록 불러오기'));
      expect(find.byType(Dialog), findsOneWidget);
      expect(find.byType(BottomSheet), findsNothing);
      expect(
        tester.getSize(find.byType(BackupCodeSheet)).width,
        lessThanOrEqualTo(AdaptiveSheet.maxDialogWidth),
      );

      await _tap(tester, find.byKey(backupCodeFieldKey).hitTestable());
      await _tap(tester, find.text('취소'));

      await _tap(tester, find.byKey(RecordsSlot.deleteAccount));
      expect(find.byType(DeleteAccountConfirm), findsOneWidget);
      expect(find.byType(Dialog), findsOneWidget);
      expect(find.byType(BottomSheet), findsNothing);
    });
  });
}
