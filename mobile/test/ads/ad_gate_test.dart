import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/ads/ad_gate.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

/// 안드로이드 비구독자의 기본 입력 — 한 축만 바꿔 가며 본다.
AdGate gateWith({
  UmpStatus? ump = const UmpStatus(
    consent: ConsentStatus.notRequired,
    privacyOptionsRequired: false,
  ),
  TrackingStatus tracking = TrackingStatus.notSupported,
  bool? entitled = false,
}) => adGateFor(ump: ump, tracking: tracking, entitled: entitled);

void main() {
  group('UMP 상태 4종', () {
    test('notRequired(EEA 밖)는 광고를 로드한다', () {
      final gate = gateWith();

      expect(gate.canLoadAds, isTrue);
      expect(gate.showsBannerSlot, isTrue);
      expect(gate.showsPrivacyOptions, isFalse);
    });

    test('obtained(동의함)도 광고를 로드한다', () {
      final gate = gateWith(
        ump: const UmpStatus(
          consent: ConsentStatus.obtained,
          privacyOptionsRequired: true,
        ),
      );

      expect(gate.canLoadAds, isTrue);
      // EEA 사용자는 S4 에서 선택을 바꿀 수 있어야 한다(US 34).
      expect(gate.showsPrivacyOptions, isTrue);
    });

    test('required(폼 뒤에도 동의 안 함)는 광고를 로드하지 않는다', () {
      final gate = gateWith(
        ump: const UmpStatus(
          consent: ConsentStatus.required,
          privacyOptionsRequired: true,
        ),
      );

      expect(gate.canLoadAds, isFalse);
      // 슬롯은 그대로 예약한다 — 구독자가 아니면 자리가 사라지지 않는다.
      expect(gate.showsBannerSlot, isTrue);
      expect(gate.showsPrivacyOptions, isTrue);
    });

    test('unknown(동의 조회 실패)은 이번 세션 광고가 없다', () {
      final gate = gateWith(ump: const UmpStatus.failed());

      expect(gate.canLoadAds, isFalse);
      expect(gate.showsPrivacyOptions, isFalse);
      // 비구독자라 힌트에는 여전히 광고가 필요한데 그 광고를 띄울 수 없다 →
      // 버튼은 비활성이고 화면이 안내를 띄운다.
      expect(gate.hintPreviewNeedsAd, isTrue);
      expect(gate.canPreviewHint, isFalse);
    });

    test('UMP 를 아직 돌리지 않았으면 광고도 개인정보 항목도 없다', () {
      final gate = gateWith(ump: null);

      expect(gate.canLoadAds, isFalse);
      expect(gate.showsPrivacyOptions, isFalse);
    });
  });

  group('구독 권한', () {
    test('구독자는 모든 광고가 없고 힌트에 광고가 필요 없다 (US 31·32)', () {
      final gate = gateWith(
        ump: const UmpStatus(
          consent: ConsentStatus.obtained,
          privacyOptionsRequired: false,
        ),
        entitled: true,
      );

      expect(gate.canLoadAds, isFalse);
      expect(gate.showsBannerSlot, isFalse);
      expect(gate.hintPreviewNeedsAd, isFalse);
      // 광고를 안 봐도 힌트는 바로 열 수 있다.
      expect(gate.canPreviewHint, isTrue);
    });

    test('구독자도 EEA 면 광고 개인정보 설정은 남는다', () {
      final gate = gateWith(
        ump: const UmpStatus(
          consent: ConsentStatus.obtained,
          privacyOptionsRequired: true,
        ),
        entitled: true,
      );

      expect(gate.showsPrivacyOptions, isTrue);
    });

    test('권한을 아직 모르면(null) 비구독자로 다룬다', () {
      final gate = gateWith(entitled: null);

      expect(gate.canLoadAds, isTrue);
      expect(gate.showsBannerSlot, isTrue);
      expect(gate.hintPreviewNeedsAd, isTrue);
    });
  });

  group('ATT (iOS)', () {
    test('아직 묻지 않았으면 광고를 로드하지 않는다', () {
      final gate = gateWith(tracking: TrackingStatus.notDetermined);

      expect(gate.canLoadAds, isFalse);
      expect(gate.showsBannerSlot, isTrue);
    });

    test('허용·거부 둘 다 광고는 로드된다 — UMP 와 별개 상태다', () {
      for (final tracking in [
        TrackingStatus.authorized,
        TrackingStatus.denied,
        TrackingStatus.restricted,
      ]) {
        expect(
          gateWith(tracking: tracking).canLoadAds,
          isTrue,
          reason: '$tracking',
        );
      }
    });
  });
}
