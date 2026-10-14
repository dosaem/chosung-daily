import 'package:chosung/notifications/notification_plan.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 서버가 KST 로 정한 퍼즐 날짜(`GET /puzzles/today` 의 `date`)를 완료 집합의
/// 열쇠로 쓸 `yyyy-MM-dd` 로 적는다.
String puzzleDateKey(DateTime date) =>
    '${date.year.toString().padLeft(4, '0')}-'
    '${date.month.toString().padLeft(2, '0')}-'
    '${date.day.toString().padLeft(2, '0')}';

/// KST 오늘보다 이전 날짜를 버린다.
///
/// 이 집합은 **앞으로의 리마인더를 끄는 데만** 쓰인다 — 지난 날짜는 어떤
/// 리마인더와도 안 맞고, 기록의 정본은 서버(`/me/history`)다. ISO 날짜는
/// 사전순이 날짜순이라 문자열 비교로 가른다.
Set<String> pruneCompletedDates(
  Set<String> dates, {
  required String todayKst,
}) => dates.where((date) => date.compareTo(todayKst) >= 0).toSet();

/// 이 기기에서 끝낸 퍼즐 날짜가 놓이는 자리. 테스트는 이 경계를 메모리로
/// 바꿔 낀다.
abstract interface class CompletedPuzzleDateStore {
  Future<Set<String>> read();
  Future<void> write(Set<String> dates);
}

/// 기기 로컬 설정(Android SharedPreferences / iOS NSUserDefaults).
///
/// 서버에 두지 않는 이유는 US 38 이 **"이 기기에서 이미 푼 퍼즐"** 을 기준으로
/// 말하기 때문이다 — 알림은 이 기기가 걸고, 끄는 판정도 이 기기가 한다.
/// 네트워크가 없는 상태로 앱이 뜨어도(기내 모드) 리마인더 계획은 서야 한다.
class PreferencesCompletedPuzzleDateStore implements CompletedPuzzleDateStore {
  const PreferencesCompletedPuzzleDateStore();

  static const _key = 'completed_puzzle_dates';

  /// 저장소 객체는 쓸 때 만든다 — `PreferencesNotificationSettingsStore` 와 같은 이유.
  SharedPreferencesAsync get _preferences => SharedPreferencesAsync();

  @override
  Future<Set<String>> read() async =>
      (await _preferences.getStringList(_key))?.toSet() ?? <String>{};

  @override
  Future<void> write(Set<String> dates) =>
      _preferences.setStringList(_key, dates.toList()..sort());
}

final completedPuzzleDateStoreProvider = Provider<CompletedPuzzleDateStore>(
  (ref) => const PreferencesCompletedPuzzleDateStore(),
);

/// 이 기기에서 끝낸(정답 또는 5회 소진) 퍼즐의 KST 날짜 집합.
///
/// 예약 계획의 입력이고, 여기에 날짜가 하나 더해지는 것이 곧 "리마인더 취소"
/// 신호다 — 완료를 감지하는 곳과 알림을 다시 거는 곳을 이 값 하나로 잇는다.
class CompletedPuzzleDatesNotifier extends AsyncNotifier<Set<String>> {
  @override
  Future<Set<String>> build() async {
    final Set<String> stored;
    try {
      stored = await ref.read(completedPuzzleDateStoreProvider).read();
      // 못 읽으면 "아무것도 안 푼 것" 으로 본다. 그 날 리마인더가 한 번 더 오는
      // 건 감수할 수 있지만, 여기서 멈추면 알림이 통째로 안 간다.
      // `shared_preferences` 는 플러그인이 없으면 StateError 로 터진다.
      // ignore: avoid_catching_errors
    } on Error catch (error) {
      debugPrint('완료한 퍼즐 날짜를 읽지 못했습니다: $error');
      return const {};
    } on Exception catch (error) {
      debugPrint('완료한 퍼즐 날짜를 읽지 못했습니다: $error');
      return const {};
    }
    final pruned = pruneCompletedDates(
      stored,
      todayKst: NotificationPlan.todayKstDate(),
    );
    // 줄어들었으면 저장소도 같이 줄인다 — 안 그러면 쓸 때마다 옛 날짜가 다시 섞인다.
    if (pruned.length != stored.length) {
      await ref.read(completedPuzzleDateStoreProvider).write(pruned);
    }
    return pruned;
  }

  /// 퍼즐 하나가 끝났다. 같은 날짜를 다시 적어도 집합이라 그대로다 —
  /// 두 언어 중 하나만 풀어도 그 날은 완료다(7일 그리드·streak 과 같은 기준).
  Future<void> markCompleted(DateTime puzzleDate) async {
    final current = state.value ?? const <String>{};
    final key = puzzleDateKey(puzzleDate);
    if (current.contains(key)) return;

    final next = pruneCompletedDates({
      ...current,
      key,
    }, todayKst: NotificationPlan.todayKstDate());
    try {
      await ref.read(completedPuzzleDateStoreProvider).write(next);
      // 저장은 못 했어도 이번 실행에서는 끈 채로 둔다 — 방금 푼 퍼즐의
      // 리마인더가 오늘 저녁에 오는 게 가장 나쁜 경우다.
      // ignore: avoid_catching_errors
    } on Error catch (error) {
      debugPrint('완료한 퍼즐 날짜를 저장하지 못했습니다: $error');
    } on Exception catch (error) {
      debugPrint('완료한 퍼즐 날짜를 저장하지 못했습니다: $error');
    }
    if (ref.mounted) state = AsyncData(next);
  }
}

final completedPuzzleDatesProvider =
    AsyncNotifierProvider<CompletedPuzzleDatesNotifier, Set<String>>(
      CompletedPuzzleDatesNotifier.new,
    );
