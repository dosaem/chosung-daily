import 'package:chosung/account/social_sign_in.dart';
import 'package:chosung/api/api_client.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
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

  /// 서버 삭제가 끝난 **토큰**. `DELETE /me` 는 그 계정에 두 번 부를 수
  /// 없다 — 두 번째는 지워진 게스트 인증이라 401 이고(`app/api/me.py`
  /// `delete_me`), 그 401 이 사용자에게는 "삭제 실패" 로 보인다. 뒷단계(게스트
  /// 발급)가 실패했을 때 재시도가 거기서부터 이어지게 하려고 기억해 둔다.
  ///
  /// "삭제했다" 가 아니라 **어느 계정을** 삭제했는지를 들고 있는 이유: 그냥
  /// 참/거짓이면 발급 실패 뒤 다른 계정으로 전환했을 때 그 참이 남아 새 계정의
  /// `DELETE /me` 를 건너뛴다 — 서버에 계정이 그대로 남은 채로 "삭제했어요" 가
  /// 뜬다(D-29-4). 토큰을 바꾸는 길은 [_adopt] 말고도 있어서(시작 흐름의 401
  /// 복구, `StartupNotifier._fetchStats`) 플래그를 내리는 자리를 외우는 대신
  /// 지금 토큰과 맞춰 본다.
  String? _deletedToken;

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
      // 확인 응답이 곧 **새 계정의** `/me/stats` 다. 그걸 버리고 다시 읽으면
      // 그 재조회가 실패할 때 옛 계정 숫자가 화면에 남는다.
      final stats = await _api.fetchMyStatsWithToken(token);
      await _adopt(token, stats: stats);
      return const AccountState(switched: true);
    }, invalidCodeKey: 'account.error_backup_code');
  }

  /// `DELETE /me` → 로컬 삭제 → 새 게스트. 온보딩을 다시 보여주지 않으려고
  /// 기기 단위 플래그는 남긴다([LocalFlag.perAccount]).
  Future<void> deleteAccount() async {
    await _run(AccountAction.delete, () async {
      // 복원이 아직 안 끝났을 수 있다 — 지금 토큰을 모르면 삭제가 끝난 계정이
      // 지금 계정인지 알 수 없다(`link` 과 같은 이유로 기다렸다 읽는다).
      final current = await ref.read(guestTokenProvider.future);
      if (current == null || current != _deletedToken) {
        await _api.deleteAccount();
        _deletedToken = current;
        // 서버에서 사라진 계정의 로컬 흔적은 발급을 기다리지 않고 지금
        // 버린다 — 발급이 실패해 멈춰도 지워진 계정의 이름·기록이 화면에
        // 남아 있으면 안 된다.
        await ref.read(localFlagStoreProvider).clearPerAccount();
        ref.read(myStatsProvider.notifier).discard();
      }

      // 지운 토큰을 버리기 전에 새 토큰을 먼저 받는다(`POST /guests` 는 인증이
      // 없다). 먼저 버리면 발급이 실패했을 때 앱이 토큰 없이 남고, 그 사이
      // 끼어드는 재조회가 전부 401 이다. `_adopt` 의 `replaceWith` 가 죽은
      // 토큰을 덮어쓰므로 따로 지울 필요도 없다.
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
  ///
  /// [stats] 를 이미 읽어 뒀으면(백업 코드 확인 응답) 그걸 새 계정 값으로
  /// 쓰고, 없으면 새 토큰으로 읽는다. 읽기가 실패하면 `adopt` 가 예외를
  /// 올리고 [_run] 이 그 자리에 실패 문구를 둔다 — `refresh` 처럼 조용히
  /// 넘기면 옛 계정의 이름·기록이 새 토큰 위에 그대로 남는다.
  Future<void> _adopt(String token, {MyStats? stats}) async {
    await ref.read(guestTokenProvider.notifier).replaceWith(token);
    // 홈 보드는 무효화가 아니라 **폐기**다 — 무효화는 다시 읽는 동안 옛 계정
    // 보드를 값으로 남겨 두고(`copyWithPrevious`), 그 보드에서 누른 제출이 새
    // 계정의 시도를 소비한다(D-29-5, `TodayPuzzleNotifier.discard`). 순위는
    // 계정이 아니라 오늘·언어로 갈리는 공용 데이터라 무효화로 충분하다.
    // 7일 칸도 같은 이유로 **폐기**다 — 무효화는 다시 읽는 동안 옛 계정의
    // 칸을 값으로 남겨 둬(`copyWithPrevious`) 화면이 그걸 계속 고른다.
    discardTodayPuzzle(ref);
    discardHistory(ref);
    ref.invalidate(leaderboardProvider);
    await ref.read(myStatsProvider.notifier).adopt(stats);
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
