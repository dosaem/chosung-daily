import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 지금 돌고 있는 계정의 **세대**. 게스트 토큰이 바뀔 때마다(= 계정 경계를
/// 넘을 때마다) 하나 올라간다.
///
/// 왜 따로 세는가: 토큰을 바꾸면 화면들이 들고 있는 값은 **다른 사람의 값**이
/// 된다. Riverpod 의 `invalidate` 는 다시 읽는 동안 그 값을 지우지 않고
/// (`AsyncValue.copyWithPrevious`) 그대로 남겨 두므로, 옛 계정 화면에서 만든
/// 쓰기 요청이 새 계정으로 나갈 수 있다(D-29-5 — 옛 보드에서 누른 제출이 새
/// 계정의 시도를 소비했다). `ApiClient` 는 매 요청 **지금** 토큰을 읽어 Bearer
/// 에 붙이므로 보내고 나서 걸러낼 방법이 없다.
///
/// 그래서 "이 값을 만든 계정 = 지금 계정" 을 **한 자리에서** 비교한다
/// ([sendIfSameAccount]). 화면마다 제 방식으로 막으면 한 곳을 빼먹고, 빼먹은
/// 곳이 곧 남의 계정에 쓰는 길이 된다.
class AccountEpochNotifier extends Notifier<int> {
  @override
  int build() => 0;

  /// 토큰을 바꾼 자리에서만 부른다(`GuestTokenNotifier.replaceWith`·`clear` —
  /// 앱에서 토큰이 바뀌는 길은 그 둘뿐이다). 세는 자리가 하나여야 "이 값을
  /// 만든 계정" 이라는 말이 뜻을 갖는다.
  void bump() => state = state + 1;

  /// [epoch] 에서 만든 값으로 나가는 **쓰기**를 감싼다. 그 사이 계정이
  /// 바뀌었으면 요청을 보내지 않고 null 을 돌려준다 — 부른 쪽은 그 값이 이미
  /// 남의 것이라는 뜻으로 읽고 자기 상태를 버린다.
  ///
  /// 토큰을 읽는 곳(`_authorized()`)과 이 비교 사이에 `await` 가 없어야 한다 —
  /// 그래서 요청을 **만드는** 자리에서 감싼다. 응답이 null 일 수 있는 쓰기에는
  /// 쓰지 않는다: 거절과 응답을 구별할 수 없다.
  Future<T?> sendIfSameAccount<T>(int epoch, Future<T> Function() send) async =>
      epoch == state ? await send() : null;

  /// 계정 데이터를 **읽는** 조회를 감싼다. 떠날 때의 세대를 적어 두고 응답이
  /// 오면 다시 본다 — 그 사이 계정이 바뀌었으면 성공·실패·값 없음 어느 쪽이든
  /// `null` 을 돌려준다. `null` 은 "값이 없다" 가 아니라 **"이 응답은 남의
  /// 것이다, 상태에 반영하지 마라"** 다([sendIfSameAccount] 와 같은 약속).
  ///
  /// 왜 값 쪽에서 "쓰지 말라" 를 표현하지 않는가: 조회 결과 자체로 그걸
  /// 말하면(예: 보드 없음 = null) 부른 쪽이 "현재 상태를 비우라" 로 읽어,
  /// 버려야 할 응답이 이미 올라온 새 계정 값을 지운다(D-29-6). 버릴 응답은
  /// 값의 자리 밖에서 가려낸다.
  Future<AsyncValue<T>?> fetchIfSameAccount<T>(
    Future<T> Function() fetch,
  ) async {
    final epoch = state;
    final loaded = await AsyncValue.guard(fetch);
    return epoch == state ? loaded : null;
  }
}

/// `build` 가 돌려주는 **첫 조회**의 결과를 상태 값으로 고른다.
///
/// 프레임워크는 `build` 가 돌려준 future 가 끝나면 세대·계정 검사를 거치지
/// 않고 그 값을 바로 상태에 쓴다 — 조회 쪽에서 commit 을 건너뛸 방법이 없다.
/// 그래서 버려야 하는 응답([loaded] 가 null)에는 **지금 상태**를 그대로
/// 돌려줘 그 쓰기가 아무것도 바꾸지 않게 만든다(D-29-6). 오류 상태였으면 같은
/// 오류를 다시 던져 오류 카드도 그대로 남는다.
///
/// [current] 를 콜백으로 받는 이유: provider 가 이미 버려졌으면 `state` 를
/// 읽을 수 없다. 그 경우엔 프레임워크도 결과를 쓰지 않으므로 아무 값이나
/// 돌려줘도 된다.
T? initialStateOrCurrent<T>(
  AsyncValue<T>? loaded,
  AsyncValue<T> Function() current,
) {
  final effective = loaded ?? current();
  if (effective case AsyncError(:final error, :final stackTrace)) {
    Error.throwWithStackTrace(error, stackTrace);
  }
  return effective.value;
}

final accountEpochProvider = NotifierProvider<AccountEpochNotifier, int>(
  AccountEpochNotifier.new,
);
