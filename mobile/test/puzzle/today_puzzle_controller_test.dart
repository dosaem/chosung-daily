import 'dart:async';

import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/puzzle/today_puzzle_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';

ProviderContainer _container(FakeApiClient api) {
  final container = ProviderContainer(
    retry: noAutoRetry,
    overrides: [apiClientProvider.overrideWithValue(api)],
  );
  addTearDown(container.dispose);
  return container;
}

TodayPuzzleReady _ready(TodayState state) => state as TodayPuzzleReady;

void main() {
  // AppLifecycleListener 는 binding 이 있어야 만들어진다.
  TestWidgetsFlutterBinding.ensureInitialized();

  test('시작하면 오늘 퍼즐을 한 번 읽는다', () async {
    final api = FakeApiClient(puzzle: fakeTodayPuzzle(attemptsLeft: 3));
    final container = _container(api);

    final state = await container.read(todayPuzzleProvider.future);

    expect(_ready(state).puzzle.attemptsLeft, 3);
    expect(_ready(state).notice, isNull);
    expect(api.fetchTodayPuzzleCalls, 1);
  });

  test('퍼즐이 아직 없으면 "퍼즐 없음" 상태다', () async {
    final api = FakeApiClient()
      ..fetchTodayPuzzleError = const NoPuzzleTodayApiException(
        code: 'NO_PUZZLE_TODAY',
        message: '아직 준비되지 않았습니다.',
      );
    final container = _container(api);

    final state = await container.read(todayPuzzleProvider.future);

    expect(state, isA<TodayNoPuzzle>());
  });

  test('네트워크 오류는 오류로 남긴다 — 화면이 오프라인 배너를 고른다', () async {
    final api = FakeApiClient()
      ..fetchTodayPuzzleError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
    final container = _container(api);

    await expectLater(
      container.read(todayPuzzleProvider.future),
      throwsA(isA<NetworkApiException>()),
    );
  });

  test('재시도는 다시 읽는다', () async {
    final api = FakeApiClient()
      ..fetchTodayPuzzleError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
    final container = _container(api);

    await expectLater(
      container.read(todayPuzzleProvider.future),
      throwsA(isA<NetworkApiException>()),
    );

    api.fetchTodayPuzzleError = null;
    container.read(todayPuzzleProvider.notifier).retry();
    final state = await container.read(todayPuzzleProvider.future);

    expect(state, isA<TodayPuzzleReady>());
    expect(api.fetchTodayPuzzleCalls, 2);
  });

  group('제출', () {
    test('화면에 그린 puzzle_id 를 같이 보내고 보드에 한 행이 쌓인다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 42));
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final recorded = await container
          .read(todayPuzzleProvider.notifier)
          .submit('지하촌역');

      expect(recorded, isTrue);
      expect(api.submittedGuesses.single.puzzleId, 42);
      expect(api.submittedGuesses.single.guess, '지하촌역');
      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.attempts.single.feedback, [true, false, false, true]);
      expect(state.puzzle.attemptsLeft, 4);
      expect(state.submitting, isFalse);
    });

    test('글자 수가 안 맞으면 서버까지 가지 않는다', () async {
      final api = FakeApiClient();
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final recorded = await container
          .read(todayPuzzleProvider.notifier)
          .submit('지하');

      expect(recorded, isFalse);
      expect(api.submittedGuesses, isEmpty);
    });

    // 자정 경과·다른 기기에서 언어 변경(US 3b).
    test('409 면 재조회하고 "새 퍼즐이 있어요" 를 남긴다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41))
        ..submitGuessError = const PuzzleChangedApiException(
          code: 'PUZZLE_CHANGED',
          message: '퍼즐이 바뀌었어요.',
        );
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      // 서버는 이미 새 퍼즐을 들고 있다.
      api.puzzle = fakeTodayPuzzle(puzzleId: 42);
      final recorded = await container
          .read(todayPuzzleProvider.notifier)
          .submit('지하촌역');

      expect(recorded, isFalse);
      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.puzzleId, 42);
      expect(state.puzzle.attempts, isEmpty);
      expect(state.notice, TodayNotice.puzzleChanged);
      expect(api.fetchTodayPuzzleCalls, 2);
    });

    test('제출이 오프라인이면 보드를 지우지 않고 오프라인 메시지만 남긴다', () async {
      final api = FakeApiClient()
        ..submitGuessError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      await container.read(todayPuzzleProvider.notifier).submit('지하촌역');

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.notice, TodayNotice.offline);
      expect(state.puzzle.attempts, isEmpty);
      expect(state.submitting, isFalse);
    });

    test('그 밖의 오류는 인라인 제출 실패 메시지다', () async {
      final api = FakeApiClient()
        ..submitGuessError = const UnknownApiException(
          code: 'RATE_LIMITED',
          message: '너무 많습니다.',
        );
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      await container.read(todayPuzzleProvider.notifier).submit('지하촌역');

      expect(
        _ready(container.read(todayPuzzleProvider).requireValue).notice,
        TodayNotice.submitFailed,
      );
    });

    test('끝난 퍼즐은 더 제출하지 않는다', () async {
      final api = FakeApiClient(
        puzzle: fakeTodayPuzzle(
          status: PuzzleStatus.success,
          attemptsLeft: 4,
          answer: '지하철역',
        ),
      );
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final recorded = await container
          .read(todayPuzzleProvider.notifier)
          .submit('지하철역');

      expect(recorded, isFalse);
      expect(api.submittedGuesses, isEmpty);
    });
  });

  group('재조회', () {
    test('포그라운드 복귀는 다시 읽고 스켈레톤으로 돌아가지 않는다', () async {
      final api = FakeApiClient();
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      api.puzzle = fakeTodayPuzzle(attemptsLeft: 2);
      final refreshing = container.read(todayPuzzleProvider.notifier).refresh();

      // 다시 읽는 동안에도 앞의 보드가 그대로 있다(스켈레톤 깜빡임 없음).
      expect(container.read(todayPuzzleProvider).hasValue, isTrue);
      await refreshing;

      expect(
        _ready(
          container.read(todayPuzzleProvider).requireValue,
        ).puzzle.attemptsLeft,
        2,
      );
      expect(api.fetchTodayPuzzleCalls, 2);
    });

    test('포그라운드 복귀 중 퍼즐이 바뀌어 사라졌으면 "퍼즐 없음" 으로 간다', () async {
      final api = FakeApiClient();
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      api.fetchTodayPuzzleError = const NoPuzzleTodayApiException(
        code: 'NO_PUZZLE_TODAY',
        message: '아직 준비되지 않았습니다.',
      );
      await container.read(todayPuzzleProvider.notifier).refresh();

      expect(
        container.read(todayPuzzleProvider).requireValue,
        isA<TodayNoPuzzle>(),
      );
    });
  });

  // 리뷰 r1 D-25-1: 응답이 겹쳤을 때 늦게 온 응답이 최신 보드와 제출 잠금을
  // 덮어쓰면 안 된다.
  group('응답 경합', () {
    test('제출을 기다리는 동안엔 재조회가 보드를 건드리지 않는다 — 잠금도 유지된다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41));
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final gate = Completer<void>();
      api.submitGuessGate = gate;
      final submitting = container
          .read(todayPuzzleProvider.notifier)
          .submit('지하촌역');
      // 서버는 이미 다음 퍼즐을 들고 있다(자정 경과).
      api.puzzle = fakeTodayPuzzle(puzzleId: 42);

      // 포그라운드 복귀. 지금 읽어온 이력엔 방금 보낸 답이 없다.
      await container.read(todayPuzzleProvider.notifier).refresh();

      final waiting = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(waiting.puzzle.puzzleId, 41);
      expect(waiting.submitting, isTrue, reason: '중복 제출이 다시 열리면 안 된다');
      expect(api.fetchTodayPuzzleCalls, 1, reason: '제출 중 재조회는 미룬다');

      gate.complete();
      expect(await submitting, isTrue);
      // 미뤘던 재조회가 제출 뒤에 돌아간다 — 서버 보드가 정본이다.
      await pumpEventQueue();

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.puzzleId, 42);
      expect(state.puzzle.attempts, isEmpty);
      expect(state.submitting, isFalse);
      expect(api.fetchTodayPuzzleCalls, 2);
    });

    test('제출 전에 떠난 조회가 늦게 도착해도 쌓인 행을 지우지 않는다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 7));
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      // 재조회가 느리다. 이 응답은 제출 전 이력(빈 보드)이다.
      final gate = Completer<void>();
      api.fetchTodayPuzzleGate = gate;
      final refreshing = container.read(todayPuzzleProvider.notifier).refresh();

      final recorded = await container
          .read(todayPuzzleProvider.notifier)
          .submit('지하촌역');
      expect(recorded, isTrue);

      gate.complete();
      await refreshing;

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.attempts, hasLength(1));
      expect(state.puzzle.attemptsLeft, 4);
    });

    test('첫 조회가 끝나기 전의 복귀는 그 조회를 기다린다 — 두 번 읽지 않는다', () async {
      final gate = Completer<void>();
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 9))
        ..fetchTodayPuzzleGate = gate;
      final container = _container(api);
      final first = container.read(todayPuzzleProvider.future);

      // 스플래시 중 전환처럼 첫 조회가 날아가 있는 동안의 복귀.
      await container.read(todayPuzzleProvider.notifier).refresh();
      expect(api.fetchTodayPuzzleCalls, 1);

      gate.complete();
      expect(_ready(await first).puzzle.puzzleId, 9);
    });

    test('재시도로 provider 가 다시 세워지면 이전 세대의 응답은 조용히 버린다', () async {
      final api = FakeApiClient();
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final gate = Completer<void>();
      api.submitGuessGate = gate;
      final submitting = container
          .read(todayPuzzleProvider.notifier)
          .submit('지하촌역');

      // 오류 카드의 재시도와 같은 경로 — notifier 가 버려지고 새로 세워진다.
      container.read(todayPuzzleProvider.notifier).retry();
      await container.read(todayPuzzleProvider.future);

      gate.complete();
      // 버려진 notifier 에 state 를 쓰면 예외다. 쓰지 않고 false 로 돌아온다.
      expect(await submitting, isFalse);
      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.attempts, isEmpty);
      expect(state.submitting, isFalse);
    });

    test('느린 재조회 뒤에 떠난 재조회가 이긴다', () async {
      final api = FakeApiClient();
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final gate = Completer<void>();
      api
        ..fetchTodayPuzzleGate = gate
        ..puzzle = fakeTodayPuzzle(attemptsLeft: 4);
      final first = container.read(todayPuzzleProvider.notifier).refresh();

      api
        ..fetchTodayPuzzleGate = null
        ..puzzle = fakeTodayPuzzle(attemptsLeft: 3);
      await container.read(todayPuzzleProvider.notifier).refresh();

      gate.complete();
      await first;

      expect(
        _ready(
          container.read(todayPuzzleProvider).requireValue,
        ).puzzle.attemptsLeft,
        3,
      );
    });
  });

  // 리뷰 r1 D-25-2/D-25-3: 보드가 있는 상태의 실패는 보드를 지우지 않고,
  // 그 자리에 안내 + 재시도로 남아야 한다(US 8, OVERRIDES §7).
  group('보드가 있을 때의 재조회 실패', () {
    test('서버 오류면 보드를 남기고 "다시 불러오지 못했어요" 안내를 올린다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(attemptsLeft: 2));
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      api.fetchTodayPuzzleError = const ServerApiException(
        code: 'INTERNAL_ERROR',
        message: '서버 오류',
      );
      await container.read(todayPuzzleProvider.notifier).refresh();

      final async = container.read(todayPuzzleProvider);
      expect(async.hasError, isFalse, reason: '오류가 값 뒤에 숨으면 화면이 정상처럼 보인다');
      final state = _ready(async.requireValue);
      expect(state.puzzle.attemptsLeft, 2);
      expect(state.notice, TodayNotice.refreshFailed);
      expect(state.notice!.blocksInput, isFalse);
      expect(state.notice!.showsRetry, isTrue);
    });

    test('네트워크 오류면 오프라인 안내로 바꿔 입력을 잠근다', () async {
      final api = FakeApiClient();
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      api.fetchTodayPuzzleError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
      await container.read(todayPuzzleProvider.notifier).refresh();

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.notice, TodayNotice.offline);
      expect(state.notice!.blocksInput, isTrue);
    });

    // D-25-3: 앞선 안내(409·제출 실패)가 남아 있어도 지금의 오프라인을 가리면 안 된다.
    test('앞선 안내가 있어도 재조회 오프라인이 안내를 덮어쓴다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41))
        ..submitGuessError = const PuzzleChangedApiException(
          code: 'PUZZLE_CHANGED',
          message: '퍼즐이 바뀌었어요.',
        );
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      api.puzzle = fakeTodayPuzzle(puzzleId: 42);
      await container.read(todayPuzzleProvider.notifier).submit('지하촌역');
      expect(
        _ready(container.read(todayPuzzleProvider).requireValue).notice,
        TodayNotice.puzzleChanged,
      );

      api.fetchTodayPuzzleError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
      await container.read(todayPuzzleProvider.notifier).refresh();

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.notice, TodayNotice.offline);
      expect(state.puzzle.puzzleId, 42, reason: '보드는 그대로 남는다');
    });

    test('409 뒤 재조회가 실패해도 제출 잠금이 풀린다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41))
        ..submitGuessError = const PuzzleChangedApiException(
          code: 'PUZZLE_CHANGED',
          message: '퍼즐이 바뀌었어요.',
        );
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      api.fetchTodayPuzzleError = const ServerApiException(
        code: 'INTERNAL_ERROR',
        message: '서버 오류',
      );
      await container.read(todayPuzzleProvider.notifier).submit('지하촌역');

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.submitting, isFalse, reason: '입력이 영구히 잠기면 복구 경로가 없다');
      expect(state.notice, TodayNotice.refreshFailed);
      expect(state.puzzle.puzzleId, 41);
    });

    test('제출이 오프라인으로 실패한 뒤 재시도로 입력이 다시 열린다', () async {
      final api = FakeApiClient()
        ..submitGuessError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      await container.read(todayPuzzleProvider.notifier).submit('지하촌역');
      expect(
        _ready(container.read(todayPuzzleProvider).requireValue).notice,
        TodayNotice.offline,
      );

      // 연결이 돌아왔다 — 보드의 재시도가 부르는 경로.
      api.submitGuessError = null;
      await container.read(todayPuzzleProvider.notifier).refresh();

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.notice, isNull);
      expect(api.fetchTodayPuzzleCalls, 2);
    });
  });
}
