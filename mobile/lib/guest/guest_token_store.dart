import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// 게스트 토큰이 놓이는 자리. 플랫폼 채널을 타는 구현을 테스트에서 메모리로
/// 바꿔 끼우려고 인터페이스를 뒀다.
abstract interface class GuestTokenStore {
  Future<String?> read();
  Future<void> write(String token);
  Future<void> delete();
}

/// iOS Keychain / Android EncryptedSharedPreferences.
class SecureGuestTokenStore implements GuestTokenStore {
  const SecureGuestTokenStore(this._storage);

  static const _key = 'guest_token';

  final FlutterSecureStorage _storage;

  @override
  Future<String?> read() => _storage.read(key: _key);

  @override
  Future<void> write(String token) => _storage.write(key: _key, value: token);

  @override
  Future<void> delete() => _storage.delete(key: _key);
}

final guestTokenStoreProvider = Provider<GuestTokenStore>(
  // iOS: 기기를 한 번 잠금 해제한 뒤부터 읽힌다(백그라운드 알림 재예약이 토큰을
  // 필요로 할 수 있다). Android: 11.x 기본값이 AES-GCM + KeyStore 래핑이다.
  (ref) => const SecureGuestTokenStore(
    FlutterSecureStorage(
      iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
    ),
  ),
);
