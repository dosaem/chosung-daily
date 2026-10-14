import 'package:chosung/api/api_models.dart';

/// 7일 그리드 한 칸의 결과. 하루에 ko·en 퍼즐이 따로 있지만 칸은 하나다
/// (SCREENS T4 "최근 7일 ● ● ○ ● ● ● ○").
///
/// 연속 기록과 같은 기준으로 합친다 — 한 언어만 맞춰도 그 날은 이어진 날이다
/// (README "03. 연속 기록은 퍼즐 언어와 무관하다"). 그래서 성공이 가장 세고,
/// 아직 끝나지 않은 언어가 남아 있으면 실패로 못 박지 않는다.
DayResult combinedDayResult(HistoryDay day) {
  final results = day.results.values;
  if (results.contains(DayResult.success)) return DayResult.success;
  if (results.contains(DayResult.inProgress)) return DayResult.inProgress;
  if (results.contains(DayResult.fail)) return DayResult.fail;
  return DayResult.none;
}
