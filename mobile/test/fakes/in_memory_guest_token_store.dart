import 'package:chosung/guest/guest_token_store.dart';

/// flutter_secure_storage 는 플랫폼 채널을 타므로 위젯 테스트에서 쓸 수 없다.
/// 저장소 경계만 메모리로 바꾸고 나머지 흐름은 실제 코드를 그대로 돌린다.
class InMemoryGuestTokenStore implements GuestTokenStore {
  InMemoryGuestTokenStore([this.token]);

  String? token;
  int writes = 0;
  int deletes = 0;

  @override
  Future<String?> read() async => token;

  @override
  Future<void> write(String token) async {
    this.token = token;
    writes++;
  }

  @override
  Future<void> delete() async {
    token = null;
    deletes++;
  }
}
