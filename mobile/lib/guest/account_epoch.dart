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
  /// 그래서 요청을 **만드는** 자리에서 감싼다.
  Future<T?> sendIfSameAccount<T>(int epoch, Future<T> Function() send) async =>
      epoch == state ? await send() : null;
}

final accountEpochProvider = NotifierProvider<AccountEpochNotifier, int>(
  AccountEpochNotifier.new,
);
