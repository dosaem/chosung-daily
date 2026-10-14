import 'package:chosung/analytics/analytics_event.dart';
import 'package:chosung/analytics/firebase_analytics_service.dart';
import 'package:chosung/config/firebase_bootstrap.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 분석 접점(스펙 §B.20 — 서비스 클래스 하나 + 테스트 no-op).
///
/// 메서드를 이벤트마다 두지 않고 [AnalyticsEvent] 하나를 받는다 — 이름·파라미터
/// 표가 `analytics_event.dart` 한 곳에만 있어야 Firebase 구현과 no-op 구현이
/// 서로 다른 이름을 보낼 수 없다.
// 멤버가 하나뿐이라 함수 타입으로도 되지만, 스펙 §B.20 이 요구하는 "분석 서비스
// 클래스 1개 + 테스트 no-op" 의 자리를 이름 있는 타입으로 둔다 — 호출부가
// `ref.read(analyticsServiceProvider)` 로 읽는 대상이 무엇인지 드러난다.
// ignore: one_member_abstracts
abstract interface class AnalyticsService {
  Future<void> log(AnalyticsEvent event);
}

/// 아무 데도 보내지 않는 구현. Firebase 초기화를 건너뛴 빌드(설정 파일이 없는
/// CI·새로 클론한 로컬)가 쓰고, 테스트는 [logged] 로 "무엇을 찍었는지" 를 본다 —
/// 플랫폼 채널도 네트워크도 타지 않는다.
class NoopAnalyticsService implements AnalyticsService {
  final List<AnalyticsEvent> logged = [];

  @override
  Future<void> log(AnalyticsEvent event) async => logged.add(event);
}

/// 시작할 때 Firebase 가 떴는지. `main.dart` 가 실제 결과로 덮는다 —
/// 기본값을 [FirebaseBootstrap.skipped] 로 둔 건 덮는 걸 잊었을 때
/// 초기화되지 않은 Firebase 를 부르다 죽지 않게 하려는 쪽이다.
final firebaseBootstrapProvider = Provider<FirebaseBootstrap>(
  (ref) => FirebaseBootstrap.skipped,
);

/// Firebase 가 안 떴으면 이벤트를 보낼 곳이 없다 — 호출부마다 try/catch 를
/// 들지 않게 여기서 한 번 고른다.
final analyticsServiceProvider = Provider<AnalyticsService>(
  (ref) => switch (ref.watch(firebaseBootstrapProvider)) {
    FirebaseBootstrap.initialized => FirebaseAnalyticsService(),
    FirebaseBootstrap.skipped => NoopAnalyticsService(),
  },
);
