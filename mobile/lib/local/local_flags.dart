import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// 서버가 모르는, 이 기기에만 있는 "이미 봤다" 표시들.
///
/// 값이 아니라 **봤는지 아닌지**만 남긴다 — 켜지면 다시 꺼지지 않는다.
enum LocalFlag {
  /// 첫 완료 뒤 결과 시트에 한 번 띄우는 계정 연결 안내(US 20, SCREENS S2).
  linkAccountNoticeSeen('link_account_notice_seen', perAccount: true)
  ;

  const LocalFlag(this.key, {required this.perAccount});

  /// 저장소 키. 값이 바뀌면 이미 켜진 플래그가 꺼진 것처럼 보이므로 고정이다.
  final String key;

  /// 계정 삭제 때 같이 지우는가. 계정 연결 안내는 새 게스트에게 다시
  /// 보여줘야 하니 true 고, "온보딩 3장을 이미 봤다"(티켓 28) 같은 기기
  /// 단위 플래그는 false 로 더해 삭제 뒤에도 남긴다.
  final bool perAccount;
}

/// [LocalFlag] 가 놓이는 자리. 게스트 토큰과 같은 이유로 경계를 뒀다 —
/// 플랫폼 채널을 타는 저장소를 테스트에서 메모리로 바꿔 끼운다.
///
/// 읽기·쓰기·지우기만 갈아끼우고 [clearPerAccount] 는 여기 한 번만 쓴다 —
/// "무엇을 지우는가" 는 저장소가 아니라 규칙이라, 가짜 저장소로 바꿔 끼우면
/// 정작 그 규칙이 테스트에서 빠진다.
abstract class LocalFlagStore {
  Future<bool> isSet(LocalFlag flag);
  Future<void> set(LocalFlag flag);
  Future<void> delete(LocalFlag flag);

  /// 계정 삭제가 부른다. **전부 비우지 않고** `perAccount` 인 키만 지운다 —
  /// 삭제 뒤에도 온보딩을 다시 보여주지 않으려는 것이다(티켓 29).
  Future<void> clearPerAccount() async {
    for (final flag in LocalFlag.values.where((flag) => flag.perAccount)) {
      await delete(flag);
    }
  }
}

/// 게스트 토큰과 같은 저장소(iOS Keychain / Android EncryptedSharedPreferences)
/// 를 쓴다. 비밀값은 아니지만 저장소를 하나로 두면 "이 기기에 남은 앱 데이터"
/// 가 한 곳이라, 계정 삭제가 무엇을 지우는지 세기 쉽다.
class SecureLocalFlagStore extends LocalFlagStore {
  SecureLocalFlagStore(this._storage);

  static const _on = '1';

  final FlutterSecureStorage _storage;

  @override
  Future<bool> isSet(LocalFlag flag) async =>
      await _storage.read(key: flag.key) == _on;

  @override
  Future<void> set(LocalFlag flag) => _storage.write(key: flag.key, value: _on);

  @override
  Future<void> delete(LocalFlag flag) => _storage.delete(key: flag.key);
}

final localFlagStoreProvider = Provider<LocalFlagStore>(
  (ref) => SecureLocalFlagStore(
    const FlutterSecureStorage(
      iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
    ),
  ),
);
