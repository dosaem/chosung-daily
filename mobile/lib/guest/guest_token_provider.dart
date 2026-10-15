import 'package:chosung/guest/account_epoch.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 앱 전역 게스트 토큰 상태.
///
/// ApiClient 안에 숨기지 않고 여기에 둔다 — 티켓 29(계정 연결·전환)가
/// [replaceWith] 로 값을 교체하고, 티켓 30(로컬 알림)이 변경을 구독한다.
/// ApiClient 는 매 요청마다 이 값을 읽어 Bearer 헤더에 붙인다.
class GuestTokenNotifier extends AsyncNotifier<String?> {
  GuestTokenStore get _store => ref.read(guestTokenStoreProvider);

  @override
  Future<String?> build() => _store.read();

  Future<void> replaceWith(String token) async {
    await _store.write(token);
    state = AsyncData(token);
    _crossedAccountBoundary();
  }

  Future<void> clear() async {
    await _store.delete();
    state = const AsyncData(null);
    _crossedAccountBoundary();
  }

  /// 여기가 **계정 경계**다 — 토큰이 바뀌는 길은 위의 둘뿐이고(계정 연결·전환·
  /// 삭제 후 발급, 시작 흐름의 401 복구), 그 둘을 다 지나는 자리가 여기다.
  /// 세대를 올려 두면 옛 계정 화면이 만든 쓰기가 새 계정으로 나가지 못한다
  /// ([AccountEpochNotifier]).
  void _crossedAccountBoundary() =>
      ref.read(accountEpochProvider.notifier).bump();
}

final guestTokenProvider = AsyncNotifierProvider<GuestTokenNotifier, String?>(
  GuestTokenNotifier.new,
);
