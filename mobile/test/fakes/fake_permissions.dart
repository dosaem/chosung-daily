import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/permissions/notification_permission.dart';
import 'package:chosung/permissions/tracking_permission.dart';

/// OS 권한 프롬프트 자리. 테스트는 "사용자가 뭘 눌렀는지" 를 여기에 넣는다.
class FakeNotificationPermissionRequester
    implements NotificationPermissionRequester {
  FakeNotificationPermissionRequester({
    this.result = NotificationPermission.granted,
  });

  NotificationPermission result;
  int requests = 0;

  @override
  Future<NotificationPermission> request() async {
    requests++;
    return result;
  }
}

class FakeTrackingAuthorization implements TrackingAuthorization {
  FakeTrackingAuthorization({this.result = TrackingStatus.authorized});

  TrackingStatus result;
  int requests = 0;

  @override
  Future<TrackingStatus> request() async {
    requests++;
    return result;
  }
}
