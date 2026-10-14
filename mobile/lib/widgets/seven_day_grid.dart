import 'package:chosung/api/api_models.dart';
import 'package:chosung/records/history_grid.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// S4 최근 7일 미니 그리드. 서버가 오래된 날짜부터 보내주므로 그대로 그린다.
class SevenDayGrid extends StatelessWidget {
  const SevenDayGrid({required this.days, super.key});

  final List<HistoryDay> days;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      for (final day in days)
        Expanded(
          child: DayCell(date: day.date, result: combinedDayResult(day)),
        ),
    ],
  );
}

/// 하루 한 칸. 색만으로 구분하지 않는다(OVERRIDES §2) — 성공은 체크, 실패는
/// X, 진행 중은 테두리만 있는 고리, 미플레이는 빈 면이다.
class DayCell extends StatelessWidget {
  const DayCell({required this.date, required this.result, super.key});

  static const dotSize = 24.0;

  final DateTime date;
  final DayResult result;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final locale = Localizations.localeOf(context).toLanguageTag();

    return Semantics(
      label: 'records.day_semantics'.tr(
        namedArgs: {
          'date': DateFormat.MMMMd(locale).format(date),
          'result': 'records.result_${result.wire}'.tr(),
        },
      ),
      child: ExcludeSemantics(
        child: Column(
          children: [
            Container(
              width: dotSize,
              height: dotSize,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: switch (result) {
                  DayResult.success => colors.tileCorrect,
                  DayResult.fail => colors.tileWrong,
                  // 진행 중은 brand 테두리만 — brand 면 채움 금지(OVERRIDES §2).
                  DayResult.inProgress => null,
                  DayResult.none => colors.muted,
                },
                border: switch (result) {
                  DayResult.inProgress => Border.all(
                    color: colors.brand,
                    width: 2,
                  ),
                  // 미플레이 면(`muted`)은 배경과 거의 같은 밝기라 헤어라인이
                  // 없으면 "칸이 없는 것" 처럼 보인다(목업 e4 의 빈 고리와 같다).
                  DayResult.none => Border.all(color: colors.border),
                  _ => null,
                },
              ),
              child: switch (result) {
                DayResult.success => Icon(
                  LucideIcons.check,
                  size: 14,
                  color: colors.tileTextOnCorrect,
                ),
                DayResult.fail => Icon(
                  LucideIcons.x,
                  size: 14,
                  color: colors.foreground,
                ),
                _ => null,
              },
            ),
            const SizedBox(height: 4),
            // 칸이 24px 라 "12일"(ko `DateFormat.d`)은 들어가지 않는다 —
            // 날짜 전체는 Semantics 가 읽어준다.
            Text(
              '${date.day}',
              style: Theme.of(
                context,
              ).textTheme.labelSmall?.copyWith(color: colors.mutedForeground),
            ),
          ],
        ),
      ),
    );
  }
}
