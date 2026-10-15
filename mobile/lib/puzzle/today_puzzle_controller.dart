import 'dart:async';

import 'package:chosung/api/api_client.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/guest/account_epoch.dart';
import 'package:chosung/puzzle/guess_rules.dart';
import 'package:chosung/puzzle/today_puzzle_state.dart';
import 'package:chosung/ranking/leaderboard_controller.dart';
import 'package:chosung/records/history_controller.dart';
import 'package:chosung/records/my_stats_controller.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// S1 오늘 탭의 상태. `GET /puzzles/today` 하나가 보드의 정본이다 —
/// 로컬에 시도 이력을 쌓지 않는다(README "04. 시도 이력을 서버가 돌려주는 이유").
///
/// 값이 null 이면 **보드를 아직 모른다** 다(= 화면은 스켈레톤). 첫 조회 전과
/// 계정이 바뀐 직후가 그 상태다([discard]) — 로딩·오류를 `TodayState` 안에
/// 또 세지 않으려고 "없음" 만 null 로 둔다(`MyStatsNotifier` 와 같은 방식).
///
/// ## 늦은 응답이 새 상태를 덮지 못하게 하는 규칙 (리뷰 r3 D-31-6)
///
/// 보드를 바꾸는 비동기 경로는 **읽기**(첫 조회·복귀 재조회·힌트 뒤 재조회·계정
/// 경계)와 **쓰기**(제출·힌트) 둘뿐이고, 둘의 경합은 한 쌍의 규칙으로만 끊는다:
///
/// 1. **쓰기가 떠 있으면 읽기를 미룬다**([_writingBoard] → [_refreshQueued],
///    쓰기가 끝나면 [_endBoardWrite] 가 돌린다). 지금 읽는 서버 보드엔 방금 보낸
///    답·힌트가 **아직 없어서**, 그 응답을 그대로 쓰면 쌓인 행이나 열린 힌트가
///    사라진다. 미루는 것이지 버리는 것이 아니다 — 복귀 재조회는 쓰기 뒤에
///    반드시 한 번 돌아간다.
/// 2. **읽기가 떠 있으면 쓰기가 세대를 올려 그 응답을 버린다**([_generation],
///    [_canCommit]). 읽기는 보드를 통째로 갈아 끼우므로 쓰기보다 과거면 쓸 수
///    없다. 반대로 쓰기 응답은 세대로 버리지 않고 **지금의 보드에 병합**한다
///    ([_boardFor]) — 겹치지 않는 칸이라 서로를 되돌릴 이유가 없다(r2 D-31-4).
///
/// 세대와 **따로** 보는 것이 계정이다(r4 D-31-7): 세대는 "더 새 요청이 떠났나"
/// 만 세고, `puzzle_id` 는 날짜·언어로만 갈리는 공용 번호라 계정이 바뀌어도
/// 같다. 그래서 쓰기는 **보낼 때**([AccountEpochNotifier.sendIfSameAccount])와
/// **올릴 때**([_boardFor]) 두 번 계정을 본다 — 보낼 때만 보면 날아간 뒤 바뀐
/// 계정의 보드에 남의 응답이 앉고, 올릴 때만 보면 옛 보드에서 누른 쓰기가 새
/// 계정에 기록된다(US 19).
///
/// 그래서 읽기 응답은 [_readBoard] → [_commitLoad] 한 곳으로만, 쓰기 응답은
/// [_boardFor] 한 곳으로만 상태에 올라간다. 경로 쌍별 고정 테스트는
/// `test/puzzle/today_puzzle_controller_test.dart` 그룹 "응답 경합" 과
/// `review/impl-evidence-31.md` "경로 쌍 표" 에 있다.
class TodayPuzzleNotifier extends AsyncNotifier<TodayState?> {
  /// 응답 경합을 끊는 세대 번호. 조회·제출은 **떠날 때** 이 번호를 올리고,
  /// 응답이 돌아오면 자기 번호가 아직 최신일 때만 상태에 쓴다. 먼저 떠난 느린
  /// 응답이 나중에 도착해 새 보드를 과거로 되돌리는 걸 막는다.
  int _generation = 0;

  /// 제출 응답을 기다리는 중인가. 그대로 쓰면 제출한 행이 사라지고 제출 잠금까지
  /// 풀려 같은 답이 두 번 들어간다.
  bool _submitting = false;

  /// 힌트 응답을 기다리는 중인가. 그대로 쓰면 열린 힌트가 사라지고 비구독자는
  /// 이미 산 같은 힌트에 보상형 광고를 다시 봐야 한다(US 4·5a).
  bool _unlockingHint = false;

  /// 보드에 **쓰는** 요청이 떠 있는가. 읽기를 미룰지는 이 하나로만 판정한다 —
  /// 경로마다 조건을 다시 쓰면 쓰기를 하나 더할 때 한 곳을 빼먹는다(클래스 주석
  /// 규칙 1).
  bool get _writingBoard => _submitting || _unlockingHint;

  /// 쓰기가 떠 있어서 미뤄둔 읽기. 쓰기가 끝나면 [_endBoardWrite] 가 돌린다.
  bool _refreshQueued = false;

  /// 지금 보드를 **어느 계정에서** 읽었는가([accountEpochProvider]). 제출은 이
  /// 값과 지금 계정을 비교해서 남의 계정에 쓰지 않는다(D-29-5).
  int _accountEpoch = 0;

  /// 제출이 끝나면(성공·실패 모두) 완료되는 future. 힌트 요청이 이걸 기다린다 —
  /// 미루는 게 아니라 **줄을 세우는** 것이라 [_refreshQueued] 와 달리 호출을
  /// 버리지 않는다(힌트를 눌렀는데 아무 일도 안 일어나면 안 된다).
  Completer<void>? _submitDone;

  ApiClient get _api => ref.read(apiClientProvider);

  AccountEpochNotifier get _account => ref.read(accountEpochProvider.notifier);

  @override
  Future<TodayState?> build() {
    // 앱 시작(= 이 provider 의 첫 빌드)과 포그라운드 복귀 때 다시 읽는다.
    // 복귀 감지를 탭 위젯이 아니라 여기에 두는 이유: 복귀 순간 사용자가 순위·
    // 기록 탭에 있을 수 있고, 그때도 오늘 보드는 새 것이어야 한다. 알림 탭으로
    // 들어오는 경로(티켓 30)도 같은 [refresh] 를 다시 쓴다.
    final lifecycle = AppLifecycleListener(
      onResume: () => unawaited(refresh()),
    );
    ref.onDispose(lifecycle.dispose);
    // 다시 빌드되는 것(= `retry()` 의 `invalidateSelf`)도 상태를 바꾸는 사건이다.
    // Riverpod 은 notifier 객체를 그대로 두고 `build` 만 다시 부르므로 세대를
    // 여기서 올리지 않으면 이전 빌드에서 떠난 응답이 새 보드에 그대로 쓰인다.
    final generation = ++_generation;
    return _initialLoad(generation);
  }

  /// 첫 조회. [_load] 를 그대로 돌려주지 않고 [initialStateOrCurrent] 를 거친다
  /// — `build` 가 돌려준 future 는 프레임워크가 [_commitLoad] 를 건너뛰고 바로
  /// 상태에 쓰기 때문이다(D-29-6). 계정이 바뀌었거나 그 사이 새 조회가
  /// 떠났으면 지금 상태를 그대로 돌려줘 그 쓰기를 무해하게 만든다.
  Future<TodayState?> _initialLoad(int generation) async {
    final loaded = await _load();
    return initialStateOrCurrent<TodayState?>(
      _canCommit(generation) ? loaded : null,
      () => ref.mounted ? state : const AsyncData<TodayState?>(null),
    );
  }

  /// 보드를 읽는다. 떠날 때의 계정을 적어 두고([_accountEpoch], 제출 가드가
  /// 쓴다) 조회는 [AccountEpochNotifier.fetchIfSameAccount] 로 감싼다 — 그
  /// 사이 계정이 바뀌었으면 이 응답은 **남의 것**이라 `null`("쓰지 마라")이
  /// 온다. 값의 자리가 아니라 그 밖에서 가려내므로, 버릴 응답이 이미 올라온
  /// 새 계정 보드를 지우지 않는다(D-29-6).
  Future<AsyncValue<TodayState?>?> _load() {
    _accountEpoch = _account.state;
    return _account.fetchIfSameAccount<TodayState?>(() async {
      try {
        return TodayPuzzleReady(puzzle: await _api.fetchTodayPuzzle());
      } on NoPuzzleTodayApiException {
        // 오류가 아니라 "아직" 이다 — 카운트다운 카드로 보여준다(OVERRIDES §7).
        return const TodayNoPuzzle();
      }
    });
  }

  /// 읽기 응답이 상태에 올라가는 **단 하나의 자리**(클래스 주석). 첫 조회만
  /// 예외다 — 프레임워크가 `build` 의 future 를 직접 쓰므로 [_initialLoad] 가
  /// 같은 역할을 한다.
  Future<void> _readBoard(int generation, {TodayNotice? notice}) async =>
      _commitLoad(await _load(), generation, notice: notice);

  /// 쓰기가 끝나면(성공·실패 모두) 한 번 부른다. 미뤄둔 읽기를 돌린다 — 쓰기
  /// 결과를 상태에 쓴 뒤에 돌리므로 서버 보드가 마지막 말이 된다(US 3a·3b).
  void _endBoardWrite() {
    if (!_refreshQueued) return;
    _refreshQueued = false;
    unawaited(refresh());
  }

  /// 오류 카드의 재시도 버튼. 처음부터 다시 돌린다(스켈레톤 → 결과).
  void retry() => ref.invalidateSelf();

  /// 계정 경계(연결·전환·삭제 후 새 게스트)에서 **보던 보드를 버리고** 새
  /// 계정의 보드를 읽는다.
  ///
  /// `ref.invalidate` 로는 안 된다: 다시 빌드하는 동안 Riverpod 이 직전 값을
  /// 새 `AsyncLoading` 에 실어 주므로(`AsyncValue.copyWithPrevious`) 화면은
  /// 옛 계정 보드를 계속 고른다. 그 보드는 로딩 표시도 오류도 없어서 입력과
  /// 제출이 열려 있고, `ApiClient` 는 매 요청 **지금** 토큰을 읽는다 — 옛
  /// 보드에서 누른 제출이 새 계정의 시도를 소비한다(D-29-5). 그래서 값을
  /// 명시적으로 비운다(`MyStatsNotifier.discard` 와 같은 이유).
  ///
  /// 세대를 올려 떠나 있던 옛 계정의 조회·제출 응답도 같이 버린다. 새 보드
  /// 조회가 실패하면 보드가 없으므로 [_commitLoad] 가 오류 카드를 세운다 —
  /// 옛 보드 위에 "다시 불러오지 못했어요" 를 올리던 길로 가지 않는다.
  Future<void> discard() async {
    final generation = ++_generation;
    _submitting = false;
    _unlockingHint = false;
    _refreshQueued = false;
    state = const AsyncData<TodayState?>(null);
    await _readBoard(generation);
  }

  /// 포그라운드 복귀·알림 탭·보드의 인라인 재시도. 이미 보드가 있으면
  /// 스켈레톤으로 돌아가지 않고 조용히 바꿔 끼운다 — 복귀마다 화면이 깜빡이면
  /// 멀쩡한 보드를 잃는다.
  Future<void> refresh() async {
    if (!ref.mounted) return;
    if (_writingBoard) {
      _refreshQueued = true;
      return;
    }
    // 첫 조회가 아직 안 끝났으면 그 조회가 가져올 결과를 기다리면 된다.
    // (`build` 가 돌려준 future 는 프레임워크가 직접 상태에 쓰기 때문에 세대
    // 검사로 버릴 수 없다 — 그래서 두 번째 조회를 아예 띄우지 않는다.)
    if (state.isLoading && !state.hasValue) return;

    await _readBoard(++_generation);
  }

  /// 답을 제출한다. 보드에 한 행이 쌓였으면 true — 그때만 화면이 입력창을 비운다.
  Future<bool> submit(String raw) async {
    final current = state.value;
    if (current is! TodayPuzzleReady) return false;

    final puzzle = current.puzzle;
    final guess = normalizeGuess(puzzle.language, raw);
    // 길이가 안 맞는 제출은 서버에서도 시도를 소비하지 않는다(400). 왕복을
    // 아끼려고가 아니라, 제출 버튼이 잠겨 있어야 할 상태를 한 곳에서 판정한다.
    if (puzzle.status.isFinished ||
        current.submitting ||
        guess.length != puzzle.length) {
      return false;
    }

    final generation = ++_generation;
    // 이 보드를 만든 계정. 필드([_accountEpoch])는 그 사이 끼어든 조회가
    // 덮어쓰므로 떠날 때 지역 변수로 고정한다 — 보낼 때와 올릴 때 **같은** 값을
    // 봐야 "이 쓰기의 주인" 이라는 말이 뜻을 갖는다.
    final epoch = _accountEpoch;
    _submitting = true;
    final submitDone = _submitDone = Completer<void>();
    state = AsyncData(TodayPuzzleReady(puzzle: puzzle, submitting: true));

    try {
      // 보드를 만든 계정이 아직 지금 계정일 때만 요청을 보낸다. 계정이 바뀐
      // 뒤면 null 이 오고, 이 보드는 남의 것이라 버린다(D-29-5). 계정 경계는
      // 보통 `AccountNotifier._adopt` 가 보드까지 버리지만, 토큰이 바뀌는 길은
      // 그것만이 아니라(시작 흐름의 401 복구) 쓰기 직전에 한 번 더 본다.
      final result = await _account.sendIfSameAccount(
        epoch,
        () => _api.submitGuess(puzzleId: puzzle.puzzleId, guess: guess),
      );
      if (result == null) {
        unawaited(discard());
        return false;
      }
      if (!_canCommit(generation)) return false;
      // 보낸 뒤에 계정이 바뀌었으면 이 응답도, 보고 있는 보드도 남의 것이다.
      // **쓰지 않는 것만으로는 모자라다**: 이 보드는 `submitting: true` 로 잠긴
      // 채 남아 입력이 영구히 막힌다. 보내기 전 거절과 같이 보드를 버린다.
      if (!_sameAccount(epoch)) {
        unawaited(discard());
        return false;
      }
      // 떠날 때의 스냅샷이 아니라 **지금의** 보드에 이 한 행을 쌓는다 — 그 사이
      // 힌트가 열렸으면(겹치지 않는 다른 칸이다) 그것까지 되돌리지 않는다.
      final board = _boardFor(puzzle.puzzleId, epoch);
      if (board == null) return false;
      final played = applyGuess(
        puzzle: board.puzzle,
        guess: guess,
        result: result,
      );
      state = AsyncData(TodayPuzzleReady(puzzle: played));
      _invalidateGuessReaders(played);
      return true;
    } on PuzzleChangedApiException {
      // 시도는 소비되지 않았다. 새 퍼즐을 읽어와 그 위에 메시지를 올린다.
      await _readBoard(generation, notice: TodayNotice.puzzleChanged);
      return false;
    } on NetworkApiException {
      _commitNotice(generation, epoch, puzzle, TodayNotice.offline);
      return false;
    } on ApiException {
      _commitNotice(generation, epoch, puzzle, TodayNotice.submitFailed);
      return false;
    } finally {
      _submitting = false;
      _submitDone = null;
      submitDone.complete();
      _endBoardWrite();
    }
  }

  /// 힌트 미리 보기. 보상형 광고를 끝까지 본 비구독자와 구독자가 **같은
  /// 호출**을 쓴다(US 4·32) — 서버는 광고 시청 여부를 알 수 없고(AdMob SSV
  /// 미사용) 시도·순위도 건드리지 않는다(US 5).
  ///
  /// 열렸으면 true. 409 는 셋 다 "다시 읽으면 된다" 로 끝난다 — 이미 열렸으면
  /// 재조회한 보드에 `hint` 가 채워져 오고(US 5a), 끝난 퍼즐·바뀐 퍼즐은
  /// 보드 자체를 새로 읽어야 한다.
  Future<bool> unlockHint() async {
    // 제출 응답을 기다리는 중이면 그 결과가 보드에 올라간 뒤에 보낸다. 끼어들면
    // 세대 번호가 바뀌어 먼저 떠난 제출 응답이 폐기되고(소비된 시도와 남은
    // 기회가 화면에서 사라진다) `submitting: true` 도 그대로 남아 입력이 잠긴
    // 채로 끝난다. 버튼을 잠그는 대신 줄을 세우는 이유: 힌트는 시도·순위를
    // 건드리지 않으므로(US 5) 제출 중에도 누를 수 있는 게 맞다.
    for (var pending = _submitDone; pending != null; pending = _submitDone) {
      await pending.future;
      if (!ref.mounted) return false;
    }

    final current = state.value;
    if (current is! TodayPuzzleReady) return false;

    final puzzle = current.puzzle;
    if (puzzle.status.isFinished || puzzle.hint != null) return false;

    // 이 보드를 만든 계정. 제출 대기를 **지나온 뒤** 읽는다 — 기다리는 사이
    // 계정이 바뀌었으면 고정해야 하는 건 지금 보고 있는 보드의 계정이다.
    final epoch = _accountEpoch;

    // 떠 있는 재조회보다 이 요청이 새 것이다. 다만 돌아왔을 때 상태에 쓸지는
    // 세대가 아니라 **같은 퍼즐인가** 로 판정한다 — 아래 참고.
    _generation++;
    _unlockingHint = true;
    try {
      // 제출과 같은 문(D-29-5): 보드를 만든 계정이 아직 지금 계정일 때만
      // 보낸다. `unlockHint` 는 String 을 돌려주므로 null 은 "보내지 않았다"
      // 하나뿐이다(`sendIfSameAccount` 의 전제). 토큰만 바뀌는 길(401 복구)
      // 에서는 이 문이 마지막이다 — 그대로 보내면 **새 계정**의 unlock 이
      // 서버에 기록된다.
      final hint = await _account.sendIfSameAccount(
        epoch,
        () => _api.unlockHint(puzzleId: puzzle.puzzleId),
      );
      if (hint == null) {
        unawaited(discard());
        return false;
      }
      // 보낸 뒤에 바뀐 계정도 같다 — 지금 보드는 **다른 게스트**의 것이라 이
      // 힌트를 올릴 자리가 아니고, 그 보드 자체도 더 보여 줄 게 아니다.
      if (!_sameAccount(epoch)) {
        unawaited(discard());
        return false;
      }
      // 힌트는 보드의 다른 부분(시도 행·남은 기회·상태)과 겹치지 않는 한 칸이고
      // 서버는 이미 열었다. 그래서 떠날 때의 스냅샷이 아니라 지금의 보드에 그
      // 칸만 올린다. 세대 번호로 버리면(그 사이 답을 제출했을 때) 화면이 열린
      // 힌트를 잃고, 비구독자는 이미 산 같은 힌트에 광고를 다시 봐야 한다
      // (US 5a). 제출 잠금·안내는 보드 쪽 사정이라 그대로 들고 간다.
      //
      // 계정은 여기서 다시 본다([_boardFor]): 날아간 뒤 계정이 바뀌었으면 지금
      // 보드는 **다른 게스트**의 것이고 `puzzle_id` 는 공용이라 같은 번호다.
      // 그 보드에 이 힌트를 올리면 서버에 unlock 이 없는 힌트가 열린 것처럼
      // 보이고 다음 재조회에서 다시 잠긴다(r4 D-31-7, US 19).
      final board = _boardFor(puzzle.puzzleId, epoch);
      if (board == null) return false;
      state = AsyncData(
        TodayPuzzleReady(
          puzzle: board.puzzle.copyWith(hint: hint, hintUnlocked: true),
          notice: board.notice,
          submitting: board.submitting,
        ),
      );
      return true;
    } on HintAlreadyUnlockedApiException {
      await _reloadAfterHint();
      return true;
    } on AlreadyFinishedApiException {
      // 그 사이 퍼즐이 끝났다(다른 기기의 제출). 보드를 새로 읽으면 결과가
      // 보이니 따로 안내하지 않는다.
      await _reloadAfterHint();
      return false;
    } on PuzzleChangedApiException {
      await _reloadAfterHint(notice: TodayNotice.puzzleChanged);
      return false;
    } on ApiException {
      // 보드는 멀쩡하다 — 안내는 힌트 카드가 자기 자리에 띄운다.
      return false;
    } finally {
      _unlockingHint = false;
      // 힌트 중 미뤄둔 복귀 재조회. 힌트가 서버에 들어간 뒤에 읽으므로 서버
      // 보드가 마지막 말이 되면서도 열린 힌트를 같이 들고 온다.
      _endBoardWrite();
    }
  }

  /// 제출 한 줄이 바꾼 다른 화면의 데이터를 버린다 — 순위(S3)와 7일 기록·
  /// streak(S4)이다. 탭을 유지하는 셸에서는 탭을 다시 열어도 위젯만 다시 보이고
  /// provider 는 그대로라, 여기서 알려주지 않으면 방금 올린 기록이 앱을 재시작할
  /// 때까지 어디에도 안 나온다(US 12·14·16a·16b).
  ///
  /// 7일 칸은 **하루의 분류가 바뀔 때마다** 다시 읽는다. 서버 `day_result`
  /// (`app/services/game_rules.py`)는 시도 0개를 `none`, 1~4회 오답을
  /// `in_progress` 로 세기 때문에, 끝나지 않은 **첫** 제출도 `미플레이 → 진행 중`
  /// 전이를 만든다(US 16a). 두 번째 오답부터는 같은 `in_progress` 라 다시 읽을
  /// 게 없다 — 매 제출마다 왕복하지 않는다.
  ///
  /// 순위·streak·누적은 오늘이 끝나야 바뀐다 — 순위는 푼 사람만 올라가고
  /// streak·누적도 확정된 결과만 센다.
  void _invalidateGuessReaders(TodayPuzzle played) {
    final finished = played.status.isFinished;
    if (finished || played.attempts.length == 1) {
      // 무효화가 아니라 재조회다 — 보던 칸을 스켈레톤으로 되돌리지 않는다.
      refreshHistory(ref);
    }
    if (!finished) return;
    ref.invalidate(leaderboardProvider);
    // streak 은 무효화가 아니라 재조회다 — 다시 빌드하면 플레이 전 시작
    // snapshot 으로 돌아간다.
    unawaited(ref.read(myStatsProvider.notifier).refresh());
  }

  /// 힌트 응답을 받은 **뒤에** 떠나는 보드 재조회(409·끝난 퍼즐·바뀐 퍼즐).
  /// 떠날 때의 세대가 아니라 새 세대로 쓴다 — 그 사이 제출이 끝나 세대가 바뀌었다는
  /// 이유로 버리면 서버가 이미 열어 둔 힌트를 화면이 못 받는다.
  ///
  /// 제출이 아직 떠 있으면 직접 읽지 않고 제출 뒤 재조회에 넘긴다 — 지금 읽는
  /// 서버 이력엔 방금 보낸 답이 없어서다([submit] 의 [_refreshQueued] 와 같은 이유).
  Future<void> _reloadAfterHint({TodayNotice? notice}) async {
    if (!ref.mounted) return;
    if (_submitting) {
      _refreshQueued = true;
      return;
    }
    // 이 조회가 힌트 중 미뤄둔 복귀 재조회의 몫까지 한다 — 바로 뒤에 같은 걸 또
    // 보내지 않는다.
    _refreshQueued = false;
    await _readBoard(++_generation, notice: notice);
  }

  /// 이 응답을 아직 상태에 써도 되는가. 그 사이 provider 가 버려졌거나(재시도)
  /// 더 새 요청이 떠났으면 버린다.
  bool _canCommit(int generation) => ref.mounted && generation == _generation;

  /// 이 쓰기가 떠날 때 보던 보드의 계정([epoch])이 아직 지금 계정인가
  /// ([accountEpochProvider] — 티켓 29 의 장치를 그대로 쓴다). `false` 면 응답을
  /// 쓰지 않는 것으로 끝내지 않고 **보드까지 버린다**: 남의 보드는 입력·제출이
  /// 열린 채라 다음 탭 한 번이 또 새 계정으로 나간다(D-29-5).
  bool _sameAccount(int epoch) => epoch == _account.state;

  /// 응답을 올릴 **지금의** 보드. 같은 퍼즐이고 같은 계정일 때만 돌려준다 —
  /// 그 사이 퍼즐이 바뀌었거나(자정·언어) 보드가 없어졌거나 계정이 바뀌었으면
  /// 이 응답은 쓸 자리가 없다.
  ///
  /// [epoch] 는 이 쓰기가 **떠날 때** 보던 보드의 계정이다. 퍼즐 번호만으로는
  /// 모자란다: `puzzle_id` 는 날짜·언어로 갈리는 공용 번호라 게스트가 바뀌어도
  /// 같은 값이고(서버는 unlock·시도를 guest_id+puzzle_id 로 기록한다), 세대로도
  /// 모자란다: 쓰기 응답은 세대로 버리지 않는 게 규칙이다(r2 D-31-4).
  TodayPuzzleReady? _boardFor(int puzzleId, int epoch) {
    if (!ref.mounted) return null;
    if (!_sameAccount(epoch)) return null;
    final current = state.value;
    if (current is! TodayPuzzleReady) return null;
    return current.puzzle.puzzleId == puzzleId ? current : null;
  }

  /// 보드는 그대로 두고 그 위에 안내 한 줄만 올린다(제출 실패 경로).
  /// 여기서도 보드는 지금 것이다 — 제출 응답을 기다리는 사이 열린 힌트를
  /// 스냅샷으로 덮어 지우지 않는다.
  ///
  /// 계정이 바뀌었으면 안내가 아니라 보드를 버린다: 스냅샷 fallback 은 **옛
  /// 계정의 보드**를 새 토큰 위에 다시 세우고, 그대로 두면 그 보드가
  /// `submitting: true` 로 잠긴 채 남는다(r4 D-31-7 과 같은 자리).
  void _commitNotice(
    int generation,
    int epoch,
    TodayPuzzle puzzle,
    TodayNotice notice,
  ) {
    if (!_canCommit(generation)) return;
    if (!_sameAccount(epoch)) {
      unawaited(discard());
      return;
    }
    state = AsyncData(
      TodayPuzzleReady(
        puzzle: _boardFor(puzzle.puzzleId, epoch)?.puzzle ?? puzzle,
        notice: notice,
      ),
    );
  }

  /// 조회 결과를 상태에 올린다.
  ///
  /// 실패했을 때 **보고 있던 보드는 지우지 않고** 그 자리에 안내 한 줄 + 재시도를
  /// 남긴다(US 8, OVERRIDES §7). 오류를 `AsyncError` 로만 두면 Riverpod 이
  /// 이전 값을 같이 들고 있어(`copyWithPrevious`) 화면은 보드를 고르고, 오류는
  /// 아무도 안 보는 곳에 남아 재조회가 실패한 걸 알 방법이 없어진다.
  /// [loaded] 가 null 이면 계정이 바뀐 뒤 도착한 **남의 응답**이다 — 지금
  /// 상태를 그대로 둔다(`fetchIfSameAccount` 의 약속).
  void _commitLoad(
    AsyncValue<TodayState?>? loaded,
    int generation, {
    TodayNotice? notice,
  }) {
    if (loaded == null || !_canCommit(generation)) return;

    if (loaded case AsyncError(:final error)) {
      final previous = state.value;
      if (previous is TodayPuzzleReady) {
        state = AsyncData(
          TodayPuzzleReady(
            puzzle: previous.puzzle,
            notice: error is NetworkApiException
                ? TodayNotice.offline
                : TodayNotice.refreshFailed,
          ),
        );
        return;
      }
      // 보드가 없으면 오류 카드가 받는다(스켈레톤 → 오류).
      state = loaded;
      return;
    }

    state = loaded.whenData(
      (value) => switch ((value, notice)) {
        (TodayPuzzleReady(:final puzzle), final TodayNotice notice) =>
          TodayPuzzleReady(puzzle: puzzle, notice: notice),
        _ => value,
      },
    );
  }
}

/// 계정·언어 경계에서 보던 보드를 버린다([TodayPuzzleNotifier.discard]).
///
/// 홈을 아직 아무도 읽지 않았으면 버릴 보드도 없다 — 거기서 `read` 로 억지로
/// 만들면 보는 사람 없는 조회가 한 번 더 나간다(`ref.invalidate` 와 같은 규칙).
void discardTodayPuzzle(Ref ref) {
  if (!ref.exists(todayPuzzleProvider)) return;
  unawaited(ref.read(todayPuzzleProvider.notifier).discard());
}

final todayPuzzleProvider =
    AsyncNotifierProvider<TodayPuzzleNotifier, TodayState?>(
      TodayPuzzleNotifier.new,
    );
