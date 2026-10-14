import Flutter
import UIKit
import UserNotifications

@main
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    GeneratedPluginRegistrant.register(with: self)
    // 알림 응답(탭)을 OS 에서 받는 입구. flutter_local_notifications 는 이 연결을
    // 앱에 맡기므로(README iOS setup / General setup), 걸지 않으면 Dart 의
    // `onDidReceiveNotificationResponse` 와 종료 상태 launch 판별이 영원히 비어
    // 있다 — 예약은 되는데 탭만 안 먹는다.
    //
    // 받을 자격은 상속받는다: `FlutterAppDelegate` 가 채택한
    // `FlutterAppLifeCycleProvider` 가 `UNUserNotificationCenterDelegate` 를
    // 상속하고, 엔진이 그 전달 메서드를 구현해 등록된 플러그인에게 넘긴다.
    UNUserNotificationCenter.current().delegate = self
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
}
