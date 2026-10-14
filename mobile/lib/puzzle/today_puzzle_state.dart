import 'package:chosung/api/api_models.dart';
import 'package:flutter/foundation.dart';

/// S1 오늘 탭이 그릴 수 있는 상태. 로딩·오류는 `AsyncValue` 가 들고 있다 —
/// 같은 걸 여기서 또 세면 "로딩이면서 데이터가 있는" 조합을 두 곳에서 맞춰야 한다.
@immutable
sealed class TodayState {
  const TodayState();
}

/// 보드가 있는 상태. 끝난 퍼즐(`status.isFinished`)도 여기다 — 보드는 그대로
/// 보이고 입력 영역만 "결과 보기" 로 바뀐다(SCREENS S1).
class TodayPuzzleReady extends TodayState {
  const TodayPuzzleReady({
    required this.puzzle,
    this.notice,
    this.submitting = false,
  });

  final TodayPuzzle puzzle;

  /// 보드를 지우지 않고 그 자리에 띄우는 인라인 메시지(OVERRIDES §7 —
  /// 토스트로 숨기지 않는다).
  final TodayNotice? notice;

  /// 제출 응답을 기다리는 중 — 입력·제출 버튼을 잠근다.
  final bool submitting;
}

/// 자정 전환 직후 그 언어의 퍼즐이 아직 없다. 카운트다운 카드 + 재시도.
class TodayNoPuzzle extends TodayState {
  const TodayNoPuzzle();
}

/// 보드 위에 띄우는 한 줄. 문구는 번역 키로만 들고 있다.
enum TodayNotice {
  /// 보고 있던 퍼즐이 바뀌어서 새로 읽어왔다(US 3b).
  puzzleChanged('today.puzzle_changed'),

  /// 연결이 끊겨 제출하지 못했다 — 상단 배너와 같이 입력을 잠근다.
  offline('today.offline'),

  /// 그 밖의 제출 실패(rate limit·서버 오류). 다시 눌러보면 된다.
  submitFailed('today.submit_failed'),

  /// 보드는 있는데 재조회가 실패했다(서버 오류·시간 초과). 보고 있던 보드를
  /// 지우지 않고 그 자리에 재시도를 둔다 — 오류를 `AsyncError` 로만 두면
  /// 이전 값이 같이 남아(`copyWithPrevious`) 화면이 정상처럼 보인다.
  refreshFailed('today.refresh_failed')
  ;

  const TodayNotice(this.messageKey);

  final String messageKey;

  /// 오프라인은 메시지만 띄우는 게 아니라 입력을 잠근다(SCREENS S1 상태).
  bool get blocksInput => this == offline;

  /// 다시 조회해야 풀리는 상태인가 — 그때만 인라인 재시도를 띄운다(US 8,
  /// OVERRIDES §7). 409·제출 실패는 제출 버튼이 그대로 살아 있어 필요 없다.
  bool get showsRetry => this == offline || this == refreshFailed;
}
