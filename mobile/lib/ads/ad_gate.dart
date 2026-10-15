import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:flutter/foundation.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

/// 이번 실행에 읽은 UMP 결과. SDK 의 [ConsentStatus] 를 그대로 들고 다닌다 —
/// 같은 네 값을 앱 전용 enum 으로 베끼면 AdMob 문서와 대조할 수 없다.
///
/// [privacyOptionsRequired] 는 동의 상태와 **별개 값**이다(SDK 의
/// `getPrivacyOptionsRequirementStatus`). 동의를 받았어도 EEA 밖이면 이게
/// false 라서 S4 에 "광고 개인정보 설정" 행이 안 생긴다.
@immutable
class UmpStatus {
  const UmpStatus({
    required this.consent,
    required this.privacyOptionsRequired,
  });

  /// 동의 정보를 못 읽었다(네트워크·폼 오류). 이번 세션은 광고가 없고 다음
  /// 시작에 다시 묻는다(스펙 §B.21) — 상태를 캐시하지 않기 때문에 재시도가
  /// 따로 필요하지 않다.
  const UmpStatus.failed()
    : consent = ConsentStatus.unknown,
      privacyOptionsRequired = false;

  final ConsentStatus consent;
  final bool privacyOptionsRequired;

  /// 광고를 요청해도 되는 동의 상태인가. `required` 는 폼을 띄운 뒤에도
  /// 동의하지 않은 것이고, `unknown` 은 조회 실패다 — 둘 다 광고가 없다.
  bool get canRequestAds => switch (consent) {
    ConsentStatus.notRequired || ConsentStatus.obtained => true,
    ConsentStatus.required || ConsentStatus.unknown => false,
  };
}

/// 광고를 어디까지 띄울 수 있는가. 입력이 셋뿐인 순수 판정이라 화면마다
/// 조건문을 다시 쓰지 않는다(스펙 §B.21 광고 게이트).
@immutable
class AdGate {
  const AdGate({
    required this.canLoadAds,
    required this.showsBannerSlot,
    required this.hintPreviewNeedsAd,
    required this.showsPrivacyOptions,
  });

  /// 배너·전면을 요청해도 되는가.
  final bool canLoadAds;

  /// 탭 바 아래 배너 슬롯 자리를 둘 것인가. 구독자만 false 다 — 광고를 못
  /// 띄우는 상태에서도 자리는 예약한다(OVERRIDES §5 레이아웃 점프 금지).
  final bool showsBannerSlot;

  /// 힌트 미리 보기에 보상형 광고가 필요한가. 구독자는 광고 없이 바로
  /// 연다(US 32).
  final bool hintPreviewNeedsAd;

  /// S4 "광고 개인정보 설정" 행을 보일 것인가(US 34).
  final bool showsPrivacyOptions;

  /// 지금 힌트 미리 보기를 쓸 수 있는가. 광고가 필요한데 그 광고를 띄울 수
  /// 없으면 버튼을 잠그고 안내를 띄운다.
  bool get canPreviewHint => !hintPreviewNeedsAd || canLoadAds;
}

/// [ump] 가 null 이면 아직 이번 실행의 UMP 흐름이 끝나지 않았다는 뜻이다
/// (iOS 에서 ATT 선택을 기다리는 동안 포함).
///
/// [entitled] 는 구독 권한이고 null 은 "아직 모른다" 다 — `/me/stats` 가
/// 오기 전까지는 **비구독자로 다룬다**. 반대로 깔면 권한을 못 읽은 모든
/// 사용자에게 광고가 사라져 수익이 0 이 되고, 권한이 확인되는 순간
/// (티켓 33 의 갱신) 슬롯이 사라지므로 구독자가 광고를 보는 시간은 시작
/// 직후 한 번의 `/me/stats` 왕복뿐이다.
AdGate adGateFor({
  required UmpStatus? ump,
  required TrackingStatus tracking,
  required bool? entitled,
}) {
  final subscriber = entitled ?? false;
  final consented = ump?.canRequestAds ?? false;
  // iOS 는 ATT 선택이 나온 뒤에 광고를 요청한다(SCREENS S6 — 안내 1장 →
  // 시스템 프롬프트 → UMP 폼). Android 는 notSupported 로 늘 통과한다.
  final trackingSettled = tracking != TrackingStatus.notDetermined;

  return AdGate(
    canLoadAds: consented && trackingSettled && !subscriber,
    showsBannerSlot: !subscriber,
    hintPreviewNeedsAd: !subscriber,
    showsPrivacyOptions: ump?.privacyOptionsRequired ?? false,
  );
}
