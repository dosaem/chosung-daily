import 'package:flutter_riverpod/flutter_riverpod.dart';

/// "지금" 을 읽는 자리. 기본은 기기 시계다.
///
/// 알림 예약은 지금 시각으로 다음 발화 순간을 고르고 **발화 시각 순**으로
/// 건다(`planNotifications`). 그래서 기기 시계를 그대로 쓰는 테스트는 돌리는
/// 시각에 따라 계획의 순서·개수가 달라져, 같은 코드가 아침엔 통과하고 낮엔
/// 깨진다(일일 알림 09:00 은 09:00 을 넘기면 '내일', 리마인더 20:00 은 아직
/// '오늘'). 읽는 자리를 provider 로 모아 **테스트만** 고정 시각을 끼운다 —
/// 기본값은 `DateTime.now` 라 앱 동작은 그대로다.
typedef Clock = DateTime Function();

final clockProvider = Provider<Clock>((ref) => DateTime.now);
