import 'package:chosung/account/social_sign_in.dart';
import 'package:chosung/api/api_client.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/guest/guest_token_provider.dart';
import 'package:chosung/local/local_flags.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/ranking/leaderboard_controller.dart';
import 'package:chosung/records/history_controller.dart';
import 'package:chosung/records/my_stats_controller.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// S4 계정 자리에서 지금 돌고 있는 일. null 이면 아무것도 안 돈다.
enum AccountAction { linkGoogle, linkApple, backupCode, delete }

/// 계정 카드·백업 코드 시트·삭제 다이얼로그가 같이 보는 상태.
@immutable
class AccountState {
  const AccountState({
    this.running,
    this.failed,
    this.error,
    this.switched = false,
  });

  /// 돌고 있는 일. 그 동안 버튼은 비활성이다 — 두 번 눌러 토큰이 두 번
  /// 바뀌는 경우를 아예 만들지 않는다(퍼즐 언어 행과 같은 방식).
  final AccountAction? running;

  /// 방금 실패한 일. 문구를 **그 일이 시작된 자리**에만 두려고 같이 들고
  /// 있는다 — 백업 코드가 틀렸다는 말이 계정 카드에도 뜨면 안 된다.
  final AccountAction? failed;

  /// 실패 문구의 번역 키. 성공하면 null 이고, 화면은 이 문구를 그 자리
  /// 아래 한 줄로 둔다(토스트로 흘려보내지 않는다, OVERRIDES §7).
  final String? error;

  /// 마지막 연결이 **다른 기기 기록으로의 전환**이었는가. 서버가 그 계정에
  /// 이미 붙은 게스트를 돌려주면 토큰이 바뀌어 온다(§A.6
  /// `link_or_switch_account`) — 전환이라고 말해 줄 근거가 그것뿐이다.
  final bool switched;

  bool get busy => running != null;

  /// [actions] 중 하나가 실패했을 때만 문구를 돌려준다.
  String? errorFor(Set<AccountAction> actions) =>
      actions.contains(failed) ? error : null;

  /// [actions] 중 하나가 지금 돌고 있는가.
  bool isRunning(Set<AccountAction> actions) => actions.contains(running);
}

/// 계정 연결·전환·백업 코드·삭제. 전부 "토큰을 바꾸고 로컬 상태를 버린 뒤
/// 서버에서 다시 읽는다" 하나로 끝난다 — 차이는 토큰을 어디서 얻느냐뿐이다.
class AccountNotifier extends Notifier<AccountState> {
  ApiClient get _api => ref.read(apiClientProvider);

  @override
  AccountState build() => const AccountState();

  /// 구글·애플 네이티브 로그인 → `POST /auth/token-exchange`.
  Future<void> link(AccountProvider provider) async {
    final action = provider == AccountProvider.google
        ? AccountAction.linkGoogle
        : AccountAction.linkApple;
    await _run(action, () async {
      final credential = await ref.read(socialSignInProvider)(provider);
      // 사용자가 로그인 창을 닫았다 — 실패가 아니라 아무 일도 없던 것이다.
      if (credential == null) return const AccountState();

      // 복원이 아직 안 끝났을 수 있다 — 지금 토큰을 모르면 "전환" 과 "연결" 을
      // 구별할 수 없으니 기다렸다 읽는다.
      final previous = await ref.read(guestTokenProvider.future);
      final token = await _api.exchangeIdToken(
        provider: provider.wire,
        idToken: credential.idToken,
        authorizationCode: credential.authorizationCode,
      );
      await _adopt(token);
      return AccountState(switched: token != previous);
    });
  }

  /// 웹 "내 기록 백업" 코드 = 그 기기의 게스트 토큰이다. 유효한지 확인하는
  /// 길은 그 토큰으로 `GET /me/stats` 를 불러보는 것뿐이다 — 백업 코드
  /// 전용 엔드포인트는 만들지 않는다(티켓 29, 웹 복원과 같은 규칙).
  Future<void> restoreWithBackupCode(String code) async {
    await _run(AccountAction.backupCode, () async {
      final token = code.trim();
      await _api.fetchMyStatsWithToken(token);
      await _adopt(token);
      return const AccountState(switched: true);
    }, invalidCodeKey: 'account.error_backup_code');
  }

  /// `DELETE /me` → 로컬 삭제 → 새 게스트. 온보딩을 다시 보여주지 않으려고
  /// 기기 단위 플래그는 남긴다([LocalFlag.perAccount]).
  Future<void> deleteAccount() async {
    await _run(AccountAction.delete, () async {
      await _api.deleteAccount();
      await ref.read(guestTokenProvider.notifier).clear();
      await ref.read(localFlagStoreProvider).clearPerAccount();

      // 토큰이 없는 동안 재조회가 끼어들면 401 이 난다 — 새 토큰을 먼저
      // 받아 두고 그 다음에 버린다.
      final token = await _api.createGuest(
        puzzleLanguage: ref.read(devicePuzzleLanguageProvider),
      );
      await _adopt(token);
      return const AccountState();
    });
  }

  /// 새 토큰을 저장하고, 옛 계정의 화면 상태를 버리고, 서버에서 다시 읽는다.
  ///
  /// 시작 흐름(`startupProvider`)을 통째로 다시 돌리지 않는 이유: 그러면
  /// 스플래시를 거쳐 홈 탭으로 튕겨 나가 사용자가 방금 누른 계정 카드를
  /// 떠나게 된다. 대신 토큰을 쓰는 provider 만 집어서 버린다.
  Future<void> _adopt(String token) async {
    await ref.read(guestTokenProvider.notifier).replaceWith(token);
    ref
      ..invalidate(todayPuzzleProvider)
      ..invalidate(historyProvider)
      ..invalidate(leaderboardProvider);
    // `/me/stats` 를 한 번 더 읽는다(백업 코드는 확인 때도 읽었다). 드문
    // 조작이라 호출 한 번을 아끼는 것보다 경로가 하나인 쪽이 낫다.
    await ref.read(myStatsProvider.notifier).refresh();
  }

  /// 같은 일이 두 번 돌지 않게 감싸고, 실패를 사용자 문구로 눕힌다.
  Future<void> _run(
    AccountAction action,
    Future<AccountState> Function() body, {
    String invalidCodeKey = 'account.error_sign_in',
  }) async {
    if (state.busy) return;
    state = AccountState(running: action, switched: state.switched);

    AccountState next;
    try {
      next = await body();
    } on ApiException catch (error) {
      next = AccountState(
        failed: action,
        error: _messageFor(error, invalidCodeKey: invalidCodeKey),
      );
    } on SocialSignInException {
      next = AccountState(failed: action, error: 'account.error_sign_in');
    }

    if (ref.mounted) state = next;
  }

  String _messageFor(ApiException error, {required String invalidCodeKey}) =>
      switch (error) {
        AccountAlreadyLinkedApiException() => 'account.error_already_linked',
        InvalidIdTokenApiException() => 'account.error_invalid_id_token',
        // 백업 코드 흐름에서는 "코드가 틀렸다", 로그인 흐름에서는 게스트
        // 토큰이 끊긴 것이라 말이 다르다.
        UnauthorizedApiException() => invalidCodeKey,
        NetworkApiException() => 'account.error_network',
        _ => 'account.error_failed',
      };
}

final accountProvider = NotifierProvider<AccountNotifier, AccountState>(
  AccountNotifier.new,
);

/// `hsseo@gmail.com` → `hs***@gmail.com`(목업 `e4_records`). 리더보드와 같은
/// 이유로 이메일 전체는 화면에 두지 않는다 — 어깨 너머로 읽히는 값이다.
String maskEmail(String email) {
  final at = email.indexOf('@');
  final local = at < 0 ? email : email.substring(0, at);
  final domain = at < 0 ? '' : email.substring(at);
  final keep = local.length < 2 ? local.length : 2;
  return '${local.substring(0, keep)}***$domain';
}
