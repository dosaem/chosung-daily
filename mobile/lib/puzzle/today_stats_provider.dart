import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 결과 시트(S2)가 읽는 오늘 퍼즐의 시도별 정답자 분포.
///
/// `isAutoDispose` 다 — 시트를 닫으면 버리고 다시 열 때 새로 읽는다. 분포는
/// 하루 동안 계속 바뀌는 값이라 아침에 읽은 값을 저녁까지 들고 있을 이유가 없다.
final FutureProvider<TodayStats> todayStatsProvider = FutureProvider(
  (ref) => ref.watch(apiClientProvider).fetchTodayStats(),
  isAutoDispose: true,
);
