import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/ads/interstitial_store.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 전면 광고 타이밍 한 곳(US 24·25, OVERRIDES §5).
///
/// 두 가지를 같이 지킨다:
/// - **첫 제출 전 금지.** 앱을 켜자마자 광고로 시작하지 않는다. 다른 기기에서
///   이미 끝낸 퍼즐을 열어 "결과 보기" 를 눌러도 이번 실행에 제출이 없었으면
///   띄우지 않는다.
/// - **퍼즐당 1회.** 플래그를 기기에 남기므로(`InterstitialStore`) 시트를 다시
///   열거나 앱을 다시 켜도 같은 퍼즐에서는 한 번뿐이다.
///
/// 광고가 실제로 뜨지 않았으면(로드 실패) 플래그를 남기지 않는다 — 실패를
/// 노출로 세면 그 퍼즐의 기회가 그냥 사라진다.
class ResultInterstitial {
  ResultInterstitial(this._ref);

  final Ref _ref;

  bool _submittedThisSession = false;

  /// 이번 실행에서 보드에 한 행이 쌓였다(제출이 서버까지 갔다).
  void markSubmitted() => _submittedThisSession = true;

  /// 결과 시트가 닫힌 뒤에 부른다. 실제로 띄웠으면 true.
  Future<bool> showAfterResultSheet({required int puzzleId}) async {
    if (!_submittedThisSession) return false;
    if (!_ref.read(adGateProvider).canLoadAds) return false;

    final store = _ref.read(interstitialStoreProvider);
    if (await store.lastShownPuzzleId() == puzzleId) return false;

    final shown = await _ref.read(adServiceProvider).showInterstitial();
    if (shown) await store.markShown(puzzleId);
    return shown;
  }
}

/// 세션 플래그(첫 제출 여부)를 들고 있어야 해서 화면이 아니라 provider 에
/// 둔다 — 탭을 옮겨도, 결과 시트를 다시 열어도 같은 객체다.
final resultInterstitialProvider = Provider<ResultInterstitial>(
  ResultInterstitial.new,
);
