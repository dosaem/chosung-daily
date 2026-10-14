import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/permissions/notification_permission.dart';
import 'package:chosung/permissions/tracking_permission.dart';

/// OS 권한 프롬프트 자리. 테스트는 "사용자가 뭘 눌렀는지" 를 여기에 넣는다.
class FakeNotificationPermissionRequester
    implements NotificationPermissionRequester {
  FakeNotificationPermissionRequester({
    this.result = NotificationPermission.granted,
    this.currentResult = NotificationPermission.notDetermined,
  });

  /// 프롬프트에서 사용자가 누를 답.
  NotificationPermission result;

  /// OS 가 "지금" 상태로 돌려줄 답(시스템 설정에서 바뀐 뒤를 만들 때 쓴다).
  NotificationPermission currentResult;

  int requests = 0;
  int currentReads = 0;

  @override
  Future<NotificationPermission> request() async {
    requests++;
    return result;
  }

  @override
  Future<NotificationPermission> current() async {
    currentReads++;
    return currentResult;
  }
}

/// 권한 상태를 고정해 두는 notifier. OS 를 묻는 경계를 거치지 않고 화면만
/// 볼 때(골든 등) 쓴다.
class FixedNotificationPermissionNotifier
    extends NotificationPermissionNotifier {
  FixedNotificationPermissionNotifier(this.fixed);

  final NotificationPermission fixed;

  @override
  NotificationPermission build() => fixed;
}

class FakeTrackingAuthorization implements TrackingAuthorization {
  FakeTrackingAuthorization({
    this.result = TrackingStatus.authorized,
    this.saved = TrackingStatus.notDetermined,
  });

  TrackingStatus result;

  /// 시스템에 남아 있는 지난 선택(두 번째 실행 이후).
  TrackingStatus saved;
  int requests = 0;

  @override
  Future<TrackingStatus> request() async {
    requests++;
    return result;
  }

  @override
  Future<TrackingStatus> current() async => saved;
}
