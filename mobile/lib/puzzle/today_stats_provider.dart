import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// `FutureProviderFamily` 타입 이름은 공개 배럴에 없다 — 타입을 적어야 하는
// 린트(`specify_nonobvious_property_types`) 때문에 여기서만 들여온다.
import 'package:flutter_riverpod/misc.dart';

/// 결과 시트(S2)가 읽는 그 퍼즐 언어의 시도별 정답자 분포.
///
/// 언어가 인자다 — 서버는 `?language=` 가 없으면 **요청 시점의 게스트 선호
/// 언어**로 집계를 고른다. 시트가 그린 퍼즐의 언어를 못 박지 않으면 다른
/// 기기에서 언어를 바꾼 뒤의 재조회가 안 푼 퍼즐의 분포를 가져온다.
///
/// `isAutoDispose` 다 — 시트를 닫으면 버리고 다시 열 때 새로 읽는다. 분포는
/// 하루 동안 계속 바뀌는 값이라 아침에 읽은 값을 저녁까지 들고 있을 이유가 없다.
final FutureProviderFamily<TodayStats, PuzzleLanguage> todayStatsProvider =
    FutureProvider.family<TodayStats, PuzzleLanguage>(
      (ref, language) =>
          ref.watch(apiClientProvider).fetchTodayStats(language: language),
      isAutoDispose: true,
    );
