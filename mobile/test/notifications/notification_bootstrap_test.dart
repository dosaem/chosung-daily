import 'package:chosung/notifications/notification_bootstrap.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:timezone/timezone.dart' as tz;

/// 시작 초기화는 **앱이 뜨는 길 위**에 있다. 여기서 던지면 알림이 아니라 앱이
/// 못 뜬다 — 플러그인이 없는 환경에서도 "알림만 끈 채" 돌아와야 한다.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('기기 시간대를 읽어 로컬 존으로 세운다', () async {
    await initializeNotifications(
      readTimeZoneName: () async => 'America/New_York',
    );

    expect(tz.local.name, 'America/New_York');
    // 이 뒤의 TZDateTime.now(tz.local) 이 기기 시각을 그대로 쓴다.
    expect(tz.TZDateTime.now(tz.local).location.name, 'America/New_York');
  });

  test('시간대 이름이 이상하면 UTC 로 시작한다 (던지지 않는다)', () async {
    await initializeNotifications(
      readTimeZoneName: () async => 'Mars/Olympus_Mons',
    );

    expect(tz.local.name, 'Etc/UTC');
  });

  test('플러그인이 없는 환경에서는 알림 기능을 끈 채 돌아온다', () async {
    // 위젯 테스트에는 플랫폼 구현이 없어서 플러그인이 `late` 인스턴스에서
    // Error 로 터진다. 그걸 받아 `available: false` 로 내려야 알림과 상관없는
    // 화면 테스트가 같이 넘어지지 않는다.
    final bootstrap = await initializeNotifications(
      readTimeZoneName: () async => 'Asia/Seoul',
    );

    expect(bootstrap.available, isFalse);
    expect(bootstrap.taps.launchedByNotification, isFalse);
    await bootstrap.taps.dispose();
  });
}
