import 'package:chosung/analytics/analytics_event.dart';
import 'package:chosung/analytics/analytics_service.dart';
import 'package:firebase_analytics/firebase_analytics.dart';

/// Firebase 에 이벤트 하나를 보낸다. 테스트가 플랫폼 채널 없이 호출을 보려고
/// 함수로 끊어 뒀다 — 외부 호출 래퍼는 이 한 줄뿐이다(스펙 §B.20).
typedef LogAnalyticsEvent =
    Future<void> Function({
      required String name,
      Map<String, Object>? parameters,
    });

class FirebaseAnalyticsService implements AnalyticsService {
  FirebaseAnalyticsService({LogAnalyticsEvent? logEvent})
    : _logEvent = logEvent ?? _logWithFirebase;

  final LogAnalyticsEvent _logEvent;

  /// `FirebaseAnalytics.instance` 는 Firebase 가 초기화돼 있어야 읽을 수 있다 —
  /// 생성자에서 미리 읽으면 Firebase 없는 빌드가 이 클래스를 만드는 순간
  /// 던진다. 그래서 보낼 때 읽는다.
  static Future<void> _logWithFirebase({
    required String name,
    Map<String, Object>? parameters,
  }) => FirebaseAnalytics.instance.logEvent(
    name: name,
    parameters: parameters,
  );

  @override
  Future<void> log(AnalyticsEvent event) => _logEvent(
    name: event.name,
    // 파라미터 없는 이벤트는 빈 Map 대신 null 로 보낸다(Firebase 쪽 기본값).
    parameters: event.parameters.isEmpty ? null : event.parameters,
  );
}
