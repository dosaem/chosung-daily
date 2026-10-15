import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/ads/interstitial_store.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 전면 광고 타이밍 한 곳(US 24·25, OVERRIDES §5).
///
/// 두 가지를 같이 지킨다:
/// - **첫 제출 전 금지.** 앱을 켜자마자 광고로 시작하지 않는다. 다른 기기에서
///   이미 끝낸 퍼즐을 열어 "결과 보기" 를 눌러도 이번 실행에 제출이 없었으면
///   띄우지 않는다.
/// - **퍼즐당 1회.** 광고를 **요청하기 전에** 그 퍼즐의 한 번을 예약하므로
///   (`InterstitialStore`) 시트를 다시 열어도, 로드 중에 다시 닫아도, 앱을 다시
///   켜도 같은 퍼즐에서는 한 번뿐이다.
///
/// 퍼즐당 1회를 **검사와 기록 두 단계로 나누지 않는다**(리뷰 r3 D-31-5). 전에는
/// 광고가 닫힌 뒤에 기록해서, 로드·표시가 진행되는 사이에 들어온 두 번째 호출이
/// 기록 전의 "아직 안 띄웠다" 를 읽고 자기 광고를 따로 띄웠다. 이제 두 겹으로
/// 막는다:
/// - [_showing]: 떠 있는 호출을 퍼즐별로 들고 있다가 두 번째 호출에 **같은
///   future 를 그대로 돌려준다**. 지도에 넣는 건 await 전의 동기 구간이라 두
///   호출이 같이 통과할 틈이 없다.
/// - 저장소 예약: 광고를 요청하기 **전에** 적는다. 광고가 뜬 채로 앱이 죽어도
///   다시 켤 때 또 뜨지 않는다.
///
/// **로드·표시가 실패해도 예약을 풀지 않는다.** 그 퍼즐의 한 번은 쓴 것으로
/// 센다. 풀어 주면 "결과 보기" 를 누를 때마다 실패한 광고를 다시 요청해 같은
/// 퍼즐에서 몇 번이고 로드를 때리게 되고(무효 트래픽), 리뷰가 세 라운드 동안
/// 짚은 "퍼즐당 1회" 의 경계가 실패 횟수에 따라 흐려진다. 잃는 건 실패한
/// 노출 한 번뿐이다.
class ResultInterstitial {
  ResultInterstitial(this._ref);

  final Ref _ref;

  bool _submittedThisSession = false;

  /// 아직 끝나지 않은 퍼즐별 호출(위 참고).
  final Map<int, Future<bool>> _showing = {};

  /// 이번 실행에서 보드에 한 행이 쌓였다(제출이 서버까지 갔다).
  void markSubmitted() => _submittedThisSession = true;

  /// 결과 시트가 닫힌 뒤에 부른다. 실제로 띄웠으면 true.
  Future<bool> showAfterResultSheet({required int puzzleId}) {
    if (_showing[puzzleId] case final showing?) return showing;

    final showing = _show(puzzleId);
    _showing[puzzleId] = showing;
    return showing.whenComplete(() => _showing.remove(puzzleId));
  }

  Future<bool> _show(int puzzleId) async {
    if (!_submittedThisSession) return false;
    if (!_ref.read(adGateProvider).canLoadAds) return false;

    final store = _ref.read(interstitialStoreProvider);
    if (await store.hasReserved(puzzleId)) return false;
    await store.reserve(puzzleId);

    return _ref.read(adServiceProvider).showInterstitial();
  }
}

/// 세션 플래그(첫 제출 여부)를 들고 있어야 해서 화면이 아니라 provider 에
/// 둔다 — 탭을 옮겨도, 결과 시트를 다시 열어도 같은 객체다.
final resultInterstitialProvider = Provider<ResultInterstitial>(
  ResultInterstitial.new,
);
