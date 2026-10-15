import 'package:chosung/local/local_flags.dart';

/// 플랫폼 채널을 타는 secure storage 대신 쓰는 메모리 저장소.
///
/// 키를 문자열 Map 으로 들고 있는 건 일부러다 — 계정 삭제가 "전부 비우기" 가
/// 아니라 **자기 키만 지우는지**를 보려면, 앱이 모르는 키를 하나 넣어 두고
/// 그게 살아남는지 봐야 한다(티켓 28 의 온보딩 플래그 자리).
class InMemoryLocalFlagStore extends LocalFlagStore {
  final Map<String, String> values = {};

  @override
  Future<bool> isSet(LocalFlag flag) async => values[flag.key] == '1';

  @override
  Future<void> set(LocalFlag flag) async => values[flag.key] = '1';

  @override
  Future<void> delete(LocalFlag flag) async => values.remove(flag.key);
}
