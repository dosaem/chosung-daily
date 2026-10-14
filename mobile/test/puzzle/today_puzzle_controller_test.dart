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
}
