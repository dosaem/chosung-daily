import 'dart:async';

import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// ATT 시스템 프롬프트 자리. 플랫폼 채널을 타므로 테스트는 이 경계를 바꿔 낀다.
abstract interface class TrackingAuthorization {
  Future<TrackingStatus> request();

  /// 시스템이 들고 있는 **지난 선택**. 프롬프트는 기기당 한 번만 뜨므로
  /// 두 번째 실행부터는 이걸 읽어야 "아직 안 물음" 과 구분된다(티켓 31).
  Future<TrackingStatus> current();
}

/// `app_tracking_transparency` 프롬프트.
class AttTrackingAuthorization implements TrackingAuthorization {
  const AttTrackingAuthorization();

  /// 사전 안내 카드가 사라지는 애니메이션이 끝난 뒤에 시스템 프롬프트를
  /// 띄운다 — 두 다이얼로그가 겹치면 iOS 가 프롬프트를 그냥 버린다.
  static const _settleDelay = Duration(milliseconds: 200);

  @override
  Future<TrackingStatus> request() async {
    await Future<void>.delayed(_settleDelay);
    return AppTrackingTransparency.requestTrackingAuthorization();
  }

  @override
  Future<TrackingStatus> current() =>
      AppTrackingTransparency.trackingAuthorizationStatus;
}

final trackingAuthorizationProvider = Provider<TrackingAuthorization>(
  (ref) => const AttTrackingAuthorization(),
);

/// 이번 실행의 ATT 상태. 티켓 31 의 광고 게이트가 UMP 와 **별개 입력**으로
/// 읽는다(스펙 §B.21 "ATT 와 UMP 는 별개 상태").
class TrackingStatusNotifier extends Notifier<TrackingStatus> {
  @override
  TrackingStatus build() {
    if (!ref.watch(isIosProvider)) return TrackingStatus.notSupported;

    // 프롬프트는 기기당 한 번뿐이다 — 두 번째 실행에서도 notDetermined 로
    // 시작하면 광고 게이트가 영원히 "ATT 를 아직 안 물었다" 로 닫힌다.
    // 그래서 지난 선택을 **비동기로** 읽어와 덮는다. 상태가 이미 바뀌어
    // 있으면(그 사이 프롬프트가 떴다) 늦게 온 값을 버린다.
    unawaited(_restoreSystemChoice());
    return TrackingStatus.notDetermined;
  }

  Future<void> _restoreSystemChoice() async {
    final TrackingStatus saved;
    try {
      saved = await ref.read(trackingAuthorizationProvider).current();
    } on Exception {
      // ATT 를 읽을 수 없는 환경(플러그인 없는 테스트 러너)에서는 "아직 안
      // 물음" 으로 남겨둔다 — 광고를 안 띄우는 쪽이 안전하다.
      return;
    }
    if (ref.mounted && state == TrackingStatus.notDetermined) state = saved;
  }

  /// iOS 에서만 프롬프트를 띄운다. Android 는 추적 권한이라는 개념이 없어
  /// 안내 장 자체가 없다(SCREENS S6).
  Future<TrackingStatus> request() async {
    if (!ref.read(isIosProvider)) return state;

    final result = await ref.read(trackingAuthorizationProvider).request();
    if (ref.mounted) state = result;
    return result;
  }
}

final trackingStatusProvider =
    NotifierProvider<TrackingStatusNotifier, TrackingStatus>(
      TrackingStatusNotifier.new,
    );
