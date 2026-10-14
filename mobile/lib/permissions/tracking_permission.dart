import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// ATT 시스템 프롬프트 자리. 플랫폼 채널을 타므로 테스트는 이 경계를 바꿔 낀다.
// ignore: one_member_abstracts
abstract interface class TrackingAuthorization {
  Future<TrackingStatus> request();
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
}

final trackingAuthorizationProvider = Provider<TrackingAuthorization>(
  (ref) => const AttTrackingAuthorization(),
);

/// 이번 실행의 ATT 상태. 티켓 31 의 광고 게이트가 UMP 와 **별개 입력**으로
/// 읽는다(스펙 §B.21 "ATT 와 UMP 는 별개 상태").
class TrackingStatusNotifier extends Notifier<TrackingStatus> {
  @override
  TrackingStatus build() => ref.watch(isIosProvider)
      ? TrackingStatus.notDetermined
      : TrackingStatus.notSupported;

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
