import 'dart:async';

import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_provider.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/puzzle/today_puzzle_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/in_memory_guest_token_store.dart';

ProviderContainer _container(FakeApiClient api, {GuestTokenStore? tokenStore}) {
  final container = ProviderContainer(
    retry: noAutoRetry,
    overrides: [
      apiClientProvider.overrideWithValue(api),
      // 토큰을 실제로 바꿔 보는 테스트만 저장소를 끼운다 — 나머지는 보드만 본다.
      if (tokenStore != null)
        guestTokenStoreProvider.overrideWithValue(tokenStore),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

TodayPuzzleReady _ready(TodayState? state) => state! as TodayPuzzleReady;

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

    // 리뷰 r1 D-31-2: 힌트 미리 보기는 제출 잠금과 무관하게 눌릴 수 있는
    // 버튼이다. 제출 응답을 기다리는 사이에 끼어들면 그 응답이 폐기돼 소비된
    // 시도가 보드에서 사라진다.
    test('제출을 기다리는 동안 힌트를 열어도 쌓인 행과 힌트가 모두 남는다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41));
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final gate = Completer<void>();
      api.submitGuessGate = gate;
      final submitting = container
          .read(todayPuzzleProvider.notifier)
          .submit('지하촌역');

      // 제출 대기 중의 힌트 탭. 서버에 보내기 전에 제출 결과를 기다려야 한다.
      final unlocking = container
          .read(todayPuzzleProvider.notifier)
          .unlockHint();
      await pumpEventQueue();
      expect(api.unlockedHintPuzzleIds, isEmpty, reason: '제출 응답 전에는 보내지 않는다');

      gate.complete();
      expect(await submitting, isTrue);
      expect(await unlocking, isTrue);

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.attempts.length, 1, reason: '소비된 시도가 사라지면 안 된다');
      expect(state.puzzle.attemptsLeft, 4);
      expect(state.puzzle.hint, '서울에 가장 많다');
      expect(state.submitting, isFalse);
      expect(api.unlockedHintPuzzleIds, [41]);
    });

    test('제출 대기 중 힌트가 실패해도 제출 결과와 잠금 해제가 남는다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41))
        ..unlockHintError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final gate = Completer<void>();
      api.submitGuessGate = gate;
      final submitting = container
          .read(todayPuzzleProvider.notifier)
          .submit('지하촌역');
      final unlocking = container
          .read(todayPuzzleProvider.notifier)
          .unlockHint();

      gate.complete();
      expect(await submitting, isTrue);
      expect(await unlocking, isFalse);

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.attempts.length, 1);
      expect(state.puzzle.hint, isNull);
      expect(
        state.submitting,
        isFalse,
        reason: '입력이 잠긴 채 남으면 재시작 전까지 못 푼다',
      );
    });

    // 리뷰 r2 D-31-4: 반대 순서 — 힌트 응답을 기다리는 사이의 제출이다. 힌트는
    // 시도·순위를 건드리지 않으므로(US 5) 그 사이 답 입력은 살아 있고, 서버는
    // 이미 힌트를 열었다. 세대 번호로 늦은 힌트 응답을 버리면 화면이 그 힌트를
    // 잃고 비구독자는 같은 힌트에 광고를 다시 봐야 한다(US 5a).
    test('힌트를 기다리는 동안 제출이 실패해도 열린 힌트는 보드에 남는다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41));
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final gate = Completer<void>();
      api.unlockHintGate = gate;
      final opening = container.read(todayPuzzleProvider.notifier).unlockHint();
      await pumpEventQueue();
      expect(api.unlockedHintPuzzleIds, [41], reason: '힌트는 이미 서버로 떠났다');

      // 힌트 응답을 기다리는 사이의 제출. 이 요청만 끊긴다.
      api.submitGuessError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
      final recorded = await container
          .read(todayPuzzleProvider.notifier)
          .submit('지하촌역');
      expect(recorded, isFalse);

      gate.complete();
      expect(await opening, isTrue);

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.hint, '서울에 가장 많다', reason: '서버가 연 힌트를 잃으면 안 된다');
      expect(state.puzzle.hintUnlocked, isTrue);
      expect(state.notice, TodayNotice.offline, reason: '제출 실패 안내는 그대로 남는다');
      expect(state.submitting, isFalse);
      expect(
        api.unlockedHintPuzzleIds,
        [41],
        reason: '광고를 다시 보고 다시 열 필요가 없다',
      );
    });

    test('힌트를 기다리는 동안 제출이 성공하면 쌓인 행과 힌트가 모두 남는다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41));
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final gate = Completer<void>();
      api.unlockHintGate = gate;
      final opening = container.read(todayPuzzleProvider.notifier).unlockHint();
      await pumpEventQueue();

      expect(
        await container.read(todayPuzzleProvider.notifier).submit('지하촌역'),
        isTrue,
      );

      gate.complete();
      expect(await opening, isTrue);

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.attempts.length, 1);
      expect(state.puzzle.attemptsLeft, 4);
      expect(state.puzzle.hint, '서울에 가장 많다');
      expect(state.submitting, isFalse);
    });

    test('제출 응답보다 힌트가 먼저 와도 제출이 그 힌트를 덮어 지우지 않는다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41));
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final hintGate = Completer<void>();
      api.unlockHintGate = hintGate;
      final opening = container.read(todayPuzzleProvider.notifier).unlockHint();
      await pumpEventQueue();

      final submitGate = Completer<void>();
      api.submitGuessGate = submitGate;
      final submitting = container
          .read(todayPuzzleProvider.notifier)
          .submit('지하촌역');
      await pumpEventQueue();

      // 제출이 아직 떠 있는 동안 힌트가 먼저 돌아온다.
      hintGate.complete();
      expect(await opening, isTrue);
      final waiting = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(waiting.puzzle.hint, '서울에 가장 많다');
      expect(waiting.submitting, isTrue, reason: '제출 잠금을 힌트가 풀면 안 된다');

      submitGate.complete();
      expect(await submitting, isTrue);

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.attempts.length, 1);
      expect(state.puzzle.hint, '서울에 가장 많다', reason: '제출이 힌트 없던 스냅샷을 쓰면 지워진다');
      expect(state.submitting, isFalse);
    });

    test('힌트가 이미 열려 있었다는 409 는 제출이 끼어들어도 보드를 다시 읽는다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41))
        ..unlockHintError = const HintAlreadyUnlockedApiException(
          code: 'HINT_ALREADY_UNLOCKED',
          message: '이미 열림',
        );
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final gate = Completer<void>();
      api.unlockHintGate = gate;
      final opening = container.read(todayPuzzleProvider.notifier).unlockHint();
      await pumpEventQueue();

      // 서버 보드에는 힌트가 열려 있다.
      api
        ..puzzle = fakeTodayPuzzle(
          puzzleId: 41,
          hint: '서울에 가장 많다',
          hintUnlocked: true,
        )
        ..submitGuessError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );
      await container.read(todayPuzzleProvider.notifier).submit('지하촌역');

      gate.complete();
      expect(await opening, isTrue);
      await pumpEventQueue();

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.hint, '서울에 가장 많다', reason: '재조회 결과가 버려지면 안 된다');
      expect(api.fetchTodayPuzzleCalls, 2);
    });

    // 리뷰 r3, 코디네이터 지시 3: 아래 네 테스트는 "경로 쌍 표" 의 빈 칸을
    // 메운다 — 리뷰어가 다음 쌍을 찾기 전에 지연 Fake 로 고정한다.
    test('첫 조회가 끝나기 전에는 제출도 힌트도 서버로 가지 않는다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41));
      final gate = Completer<void>();
      api.fetchTodayPuzzleGate = gate;
      final container = _container(api);

      final loading = container.read(todayPuzzleProvider.future);
      await pumpEventQueue();

      // 보드를 아직 모르면(= 화면은 스켈레톤) 쓸 자리가 없다.
      final notifier = container.read(todayPuzzleProvider.notifier);
      expect(await notifier.submit('지하촌역'), isFalse);
      expect(await notifier.unlockHint(), isFalse);
      expect(api.submittedGuesses, isEmpty);
      expect(api.unlockedHintPuzzleIds, isEmpty);

      gate.complete();
      await loading;
      expect(api.fetchTodayPuzzleCalls, 1, reason: '첫 조회를 두 번 띄우지 않는다');
    });

    test('제출 응답을 기다리는 동안 다시 제출해도 서버로 한 번만 간다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41));
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final gate = Completer<void>();
      api.submitGuessGate = gate;
      final first = container.read(todayPuzzleProvider.notifier).submit('지하촌역');
      await pumpEventQueue();

      // 잠금은 보드(`submitting`)가 들고 있으므로 두 번째 호출은 바로 끊긴다.
      expect(
        await container.read(todayPuzzleProvider.notifier).submit('지하철역'),
        isFalse,
      );
      expect(api.submittedGuesses, hasLength(1));

      gate.complete();
      expect(await first, isTrue);
      expect(api.submittedGuesses, hasLength(1));
      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(
        state.puzzle.attempts,
        hasLength(1),
        reason: '한 번 누른 제출이 두 행이 되면 안 된다',
      );
    });

    // 반대 순서(재조회 × 힌트). 힌트가 떠날 때 세대를 올리므로 먼저 떠난 조회의
    // 응답은 버려진다 — 그 응답엔 힌트가 없으니 쓰면 열린 힌트를 지운다.
    test('힌트보다 먼저 떠난 재조회가 늦게 도착해도 열린 힌트를 지우지 않는다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41));
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      // 복귀 재조회가 느리다. 이 응답은 힌트 전 보드(힌트 없음)다.
      final fetchGate = Completer<void>();
      api.fetchTodayPuzzleGate = fetchGate;
      final refreshing = container.read(todayPuzzleProvider.notifier).refresh();
      await pumpEventQueue();

      // 그 사이 보상형을 끝까지 보고 힌트를 연다.
      final hintGate = Completer<void>();
      api.unlockHintGate = hintGate;
      final opening = container.read(todayPuzzleProvider.notifier).unlockHint();
      await pumpEventQueue();
      hintGate.complete();
      expect(await opening, isTrue);

      // 먼저 떠난 조회가 뒤늦게 도착한다.
      fetchGate.complete();
      await refreshing;
      await pumpEventQueue();

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.hint, '서울에 가장 많다', reason: '과거 응답이 힌트를 덮으면 안 된다');
      expect(state.puzzle.hintUnlocked, isTrue);
      expect(api.unlockedHintPuzzleIds, [41]);
    });

    // 리뷰 r3 D-31-6: 힌트 응답을 기다리는 사이의 포그라운드 복귀다. 그때 읽는
    // 서버 보드엔 방금 연 힌트가 아직 없어서(제출의 `_refreshQueued` 와 같은
    // 이유) 그 응답이 힌트보다 늦게 도착해 보드를 통째로 갈아 끼우면 열린 힌트가
    // 사라진다. 화면은 다시 광고 버튼을 띄우고 비구독자는 이미 산 같은 힌트에
    // 보상형을 다시 봐야 한다(US 4·5a).
    test('힌트를 기다리는 동안 떠난 복귀 재조회가 열린 힌트를 되돌리지 않는다', () async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41));
      final container = _container(api);
      await container.read(todayPuzzleProvider.future);

      final hintGate = Completer<void>();
      api.unlockHintGate = hintGate;
      final opening = container.read(todayPuzzleProvider.notifier).unlockHint();
      await pumpEventQueue();
      expect(api.unlockedHintPuzzleIds, [41], reason: '힌트는 이미 서버로 떠났다');

      // 포그라운드 복귀. 응답을 붙잡아 둬서 힌트보다 늦게 도착하게 만든다.
      final fetchGate = Completer<void>();
      api.fetchTodayPuzzleGate = fetchGate;
      final refreshing = container.read(todayPuzzleProvider.notifier).refresh();
      await pumpEventQueue();
      // 눈에 보이는 증상(사라진 힌트)을 먼저 재니 호출 수는 받아만 둔다.
      final callsDuringHint = api.fetchTodayPuzzleCalls;

      // 힌트 쓰기가 서버에 들어간 뒤 응답이 돌아온다 — 이제 조회해도 힌트가
      // 같이 온다.
      api.puzzle = fakeTodayPuzzle(
        puzzleId: 41,
        hint: '서울에 가장 많다',
        hintUnlocked: true,
      );
      hintGate.complete();
      expect(await opening, isTrue);
      expect(
        _ready(container.read(todayPuzzleProvider).requireValue).puzzle.hint,
        '서울에 가장 많다',
      );

      // 붙잡아 둔 조회 응답이 뒤늦게 도착한다.
      fetchGate.complete();
      await refreshing;
      await pumpEventQueue();

      final state = _ready(container.read(todayPuzzleProvider).requireValue);
      expect(state.puzzle.hint, '서울에 가장 많다', reason: '서버가 연 힌트를 잃으면 안 된다');
      expect(state.puzzle.hintUnlocked, isTrue);
      expect(
        api.unlockedHintPuzzleIds,
        [41],
        reason: '광고를 다시 보고 다시 열 필요가 없다',
      );
      expect(callsDuringHint, 1, reason: '힌트 중 재조회는 미룬다 — 첫 보드 조회 하나뿐이다');
      // 미뤘던 복귀 재조회는 버리지 않는다 — 힌트 뒤에 돌아간다.
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

  test('계정이 바뀐 뒤에는 옛 보드로 제출하지 않는다', () async {
    // D-29-5 의 다른 입구: 토큰은 `AccountNotifier._adopt` 말고 시작 흐름의
    // 401 복구에서도 바뀐다(`StartupNotifier._fetchStats`). 그 길은 보드를
    // 버려 주지 않으므로, 쓰기 직전의 계정 세대 비교가 마지막 문이다.
    final api = FakeApiClient();
    final container = _container(
      api,
      tokenStore: InMemoryGuestTokenStore('guest-a'),
    );
    final board = await container.read(todayPuzzleProvider.future);
    expect(board, isA<TodayPuzzleReady>());

    // 새 계정 보드 조회는 붙잡아 둔다 — 옛 보드가 화면에 남은 그 순간을 본다.
    final gate = Completer<void>();
    api.fetchTodayPuzzleGate = gate;
    addTearDown(() {
      if (!gate.isCompleted) gate.complete();
    });
    await container.read(guestTokenProvider.notifier).replaceWith('guest-b');
    expect(
      container.read(todayPuzzleProvider).value,
      isA<TodayPuzzleReady>(),
      reason: '이 입구는 보드를 버려 주지 않는다 — 그래서 제출이 막아야 한다',
    );

    final recorded = await container
        .read(todayPuzzleProvider.notifier)
        .submit('지하촌역');

    expect(recorded, isFalse);
    expect(api.submittedGuesses, isEmpty);
    // 남의 보드는 화면에서도 사라진다(새 계정 보드를 읽는 중).
    expect(container.read(todayPuzzleProvider).value, isNull);
  });

  test('첫 조회 중 계정이 바뀌면 그 응답은 보드가 되지 않는다', () async {
    // `build` 가 돌려준 future 는 프레임워크가 세대 검사 없이 바로 상태에
    // 쓴다 — 그 사이 계정이 바뀌었으면 옛 계정 보드가 새 토큰 위에 앉는다.
    final api = FakeApiClient();
    final gate = Completer<void>();
    api.fetchTodayPuzzleGate = gate;
    final container = _container(
      api,
      tokenStore: InMemoryGuestTokenStore('guest-a'),
    );
    final pending = container.read(todayPuzzleProvider.future);

    await container.read(guestTokenProvider.notifier).replaceWith('guest-b');
    api.fetchTodayPuzzleGate = null;
    gate.complete();
    expect(await pending, isNull);

    expect(container.read(todayPuzzleProvider).value, isNull);
    expect(
      await container.read(todayPuzzleProvider.notifier).submit('지하촌역'),
      isFalse,
    );
    expect(api.submittedGuesses, isEmpty);
  });

  test('늦게 끝난 첫 조회는 새 계정의 오류 카드도 지우지 않는다', () async {
    // D-29-6 의 다른 얼굴: 늦은 첫 응답이 상태에 그대로 쓰이면 새 계정 조회가
    // 남긴 오류 카드까지 덮어, 재시도 버튼도 없는 화면이 된다.
    final api = FakeApiClient();
    final gate = Completer<void>();
    api.fetchTodayPuzzleGate = gate;
    final container = _container(
      api,
      tokenStore: InMemoryGuestTokenStore('guest-a'),
    );
    // 이 future 는 `discard` 가 상태를 비우는 순간 그 값으로 끝난다 — 붙잡아
    // 둔 첫 응답은 그보다 늦게 온다.
    final pending = container.read(todayPuzzleProvider.future);

    // 새 계정 보드 조회는 실패한다 — 보드가 없으니 오류 카드가 그 자리를 받는다.
    api
      ..fetchTodayPuzzleGate = null
      ..fetchTodayPuzzleError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
    await container.read(guestTokenProvider.notifier).replaceWith('guest-b');
    await container.read(todayPuzzleProvider.notifier).discard();
    expect(await pending, isNull);
    expect(container.read(todayPuzzleProvider).hasError, isTrue);

    // 늦게 도착한 첫 조회는 성공 응답이지만 남의 계정 것이다.
    api.fetchTodayPuzzleError = null;
    gate.complete();
    await pumpEventQueue();

    final today = container.read(todayPuzzleProvider);
    expect(today.hasError, isTrue, reason: '옛 응답이 오류 카드를 지웠다');
    expect(today.value, isNull);
  });
}
