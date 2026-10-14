import 'package:chosung/puzzle/guess_rules.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';

/// 시도 횟수별 정답자 비율 막대(OVERRIDES §6 `StatBar`, SCREENS S2 · US 9).
///
/// 내 시도 행은 **brand 가 아니라 `primary-button` 면**이다 — SCREENS 는 "내
/// 시도 행 brand 색" 이라고 쓰지만 OVERRIDES §2 가 brand 면 채움을 금지하고
/// 충돌 시 OVERRIDES 가 우선이다(목업 `e2_result` 의 막대도 검정이다).
class StatBar extends StatelessWidget {
  const StatBar({required this.byAttempt, this.myAttempt, super.key});

  /// 막대 한 줄의 높이(OVERRIDES §4 간격 스케일).
  static const barHeight = 20.0;

  /// 시도 횟수(1~5) → 비율(0~1). 서버가 안 보낸 칸은 0 으로 그린다.
  final Map<int, double> byAttempt;

  /// 내가 맞춘 회차. 못 맞췄으면 null — 분포에 내 자리가 없다.
  final int? myAttempt;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      for (var attempt = 1; attempt <= maxAttempts; attempt++) ...[
        _StatRow(
          attempt: attempt,
          ratio: byAttempt[attempt] ?? 0,
          isMine: attempt == myAttempt,
        ),
        if (attempt < maxAttempts) const SizedBox(height: 8),
      ],
    ],
  );
}

class _StatRow extends StatelessWidget {
  const _StatRow({
    required this.attempt,
    required this.ratio,
    required this.isMine,
  });

  /// 회차 라벨("3회")과 비율("40%") 칸 폭. 숫자가 흔들리지 않게 고정하되,
  /// 글자 크기를 키운 기기에서는 같은 비율로 넓힌다 — 고정 폭이면 거기서만
  /// 글자가 잘린다(잘림은 레이아웃 오류를 내지 않아 테스트로도 안 보인다).
  static const _labelWidth = 32.0;
  static const _percentWidth = 44.0;

  final int attempt;
  final double ratio;
  final bool isMine;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final textScaler = MediaQuery.textScalerOf(context);
    final percent = (ratio * 100).round();
    final style = Theme.of(context).textTheme.bodySmall?.copyWith(
      color: isMine ? colors.foreground : colors.mutedForeground,
      fontWeight: isMine ? FontWeight.w700 : FontWeight.w400,
    );

    return Semantics(
      // 색·굵기로만 "내 행" 을 말하지 않는다(US 3 과 같은 이유).
      label: [
        'result.stats_row'.plural(
          attempt,
          namedArgs: {'percent': '$percent'},
          name: 'count',
        ),
        if (isMine) 'result.stats_mine'.tr(),
      ].join(' '),
      child: ExcludeSemantics(
        child: Row(
          children: [
            SizedBox(
              width: textScaler.scale(_labelWidth),
              child: Text(
                'result.stats_attempt'.tr(namedArgs: {'count': '$attempt'}),
                textAlign: TextAlign.right,
                style: style,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Container(
                key: ValueKey('stat-track-$attempt'),
                height: StatBar.barHeight,
                color: colors.muted,
                child: FractionallySizedBox(
                  alignment: Alignment.centerLeft,
                  widthFactor: ratio.clamp(0, 1),
                  heightFactor: 1,
                  child: ColoredBox(
                    key: ValueKey('stat-fill-$attempt'),
                    color: isMine
                        ? colors.primaryButton
                        : colors.mutedForeground,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              width: textScaler.scale(_percentWidth),
              child: Text(
                'result.stats_percent'.tr(namedArgs: {'percent': '$percent'}),
                textAlign: TextAlign.right,
                style: style,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
