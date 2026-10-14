import 'package:chosung/puzzle/guess_rules.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';

/// S3 리더보드 한 줄(OVERRIDES §6 `LeaderboardRow`).
///
/// 폰도 태블릿도 같은 4칸(순위·이름·시도·시간)이다 — T3 의 "넓은 표" 는 이
/// 줄을 그대로 쓰고 폭과 머리글만 더한다. 칸 폭을 고정해야 머리글과 값이
/// 세로로 맞는다.
class LeaderboardRow extends StatelessWidget {
  const LeaderboardRow({
    required this.rank,
    required this.name,
    required this.attempts,
    required this.seconds,
    required this.isMe,
    super.key,
  });

  static const rankWidth = 44.0;
  static const attemptsWidth = 64.0;
  static const timeWidth = 76.0;

  final int rank;
  final String name;
  final int attempts;
  final int seconds;

  /// 내 행은 `brand-subtle` 면으로 강조한다(OVERRIDES §2 — brand 는 면 금지).
  final bool isMe;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final attemptsLabel = 'ranking.attempts'.tr(
      namedArgs: {'count': '$attempts'},
    );
    // 걸린 시간도 HH:MM:SS 라 카운트다운과 같은 포맷터를 쓴다.
    final timeLabel = formatCountdown(Duration(seconds: seconds));

    return Semantics(
      // 칸 4개가 따로 읽히면 어느 줄의 값인지 알 수 없다.
      label: 'ranking.row_semantics'.tr(
        namedArgs: {
          'rank': '$rank',
          'name': name,
          'attempts': attemptsLabel,
          'time': timeLabel,
        },
      ),
      selected: isMe,
      child: ExcludeSemantics(
        child: Container(
          color: isMe ? colors.brandSubtle : null,
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
          child: Row(
            children: [
              SizedBox(
                width: rankWidth,
                // 1~3위만 굵게. brand 색 글자는 쓰지 않는다(OVERRIDES §2).
                child: Text(
                  '$rank',
                  style: rank <= 3
                      ? text.titleMedium?.copyWith(fontWeight: FontWeight.w700)
                      : text.bodyMedium,
                ),
              ),
              Expanded(
                child: Text(
                  name,
                  overflow: TextOverflow.ellipsis,
                  style: isMe
                      ? text.bodyMedium?.copyWith(fontWeight: FontWeight.w600)
                      : text.bodyMedium,
                ),
              ),
              SizedBox(
                width: attemptsWidth,
                child: Text(
                  attemptsLabel,
                  textAlign: TextAlign.right,
                  style: text.bodySmall?.copyWith(
                    color: colors.mutedForeground,
                  ),
                ),
              ),
              SizedBox(
                width: timeWidth,
                child: Text(
                  timeLabel,
                  textAlign: TextAlign.right,
                  style: text.bodySmall?.copyWith(
                    color: colors.mutedForeground,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
