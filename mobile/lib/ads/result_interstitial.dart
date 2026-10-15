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

  /// 아직 끝나지 않은 퍼즐별 호출. 기록([InterstitialStore])은 광고가 **닫힌
  /// 뒤**에 남으므로 기록만으로는 "퍼즐당 1회" 를 못 지킨다 — 로드·표시가
  /// 진행되는 사이 결과 시트를 다시 닫으면 두 호출이 모두 기록 전의 "아직 안
  /// 띄웠다" 를 읽고 각자 광고를 띄운다. 떠 있는 호출이 있으면 그 future 를
  /// 그대로 돌려줘 **하나로 합친다** — 두 번째 호출도 방금 뜬 그 광고의 결과를
  /// 받는다.
  final Map<int, Future<bool>> _showing = {};

  /// 이번 실행에서 보드에 한 행이 쌓였다(제출이 서버까지 갔다).
  void markSubmitted() => _submittedThisSession = true;

  /// 결과 시트가 닫힌 뒤에 부른다. 실제로 띄웠으면 true.
  Future<bool> showAfterResultSheet({required int puzzleId}) {
    if (_showing[puzzleId] case final showing?) return showing;

    final showing = _show(puzzleId);
    _showing[puzzleId] = showing;
    // 끝나면 자리를 비운다 — 로드 실패는 기록을 남기지 않으므로(아래) 그 퍼즐의
    // 다음 시트 닫힘에서 다시 시도할 수 있어야 한다.
    return showing.whenComplete(() => _showing.remove(puzzleId));
  }

  Future<bool> _show(int puzzleId) async {
    if (!_submittedThisSession) return false;
    if (!_ref.read(adGateProvider).canLoadAds) return false;

    final store = _ref.read(interstitialStoreProvider);
    if (await store.hasShown(puzzleId)) return false;

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
