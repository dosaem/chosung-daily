import 'package:chosung/layout/app_breakpoint.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// 잠김(자물쇠 + 안내 + 보상형 버튼) / 열림(힌트 문장).
///
/// 서버가 "3번째 오답 뒤" 또는 "힌트 미리 보기를 쓴 뒤" 에만 `hint` 를 채워
/// 보내므로(스펙 §A.4) 앱은 공개 조건을 다시 계산하지 않는다 — [hint] 가
/// null 인지만 본다.
class HintCard extends StatelessWidget {
  const HintCard({required this.hint, this.onWatchAd, super.key});

  final String? hint;

  /// 보상형 광고로 힌트를 미리 여는 동작. 광고 SDK 가 들어오는 티켓 31 이
  /// 넣는다 — 그때까지 버튼은 자리만 잡고 눌리지 않는다.
  final VoidCallback? onWatchAd;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final unlocked = hint;

    return Container(
      // 카드 패딩 16(모바일) / 24(태블릿+) — OVERRIDES §4.
      padding: EdgeInsets.all(AppBreakpoint.of(context).hasRail ? 24 : 16),
      decoration: BoxDecoration(
        // 면을 깔지 않는다 — 라이트에선 카드가 없고 구분은 헤어라인뿐이다
        // (OVERRIDES §4). 다크도 같은 모양으로 둬서 두 모드가 어긋나지 않게 한다.
        border: Border.all(color: colors.border),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(
                unlocked == null ? LucideIcons.lock : LucideIcons.lightbulb,
                size: 16,
                color: colors.mutedForeground,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  unlocked ?? 'hint.locked'.tr(),
                  style: unlocked == null
                      ? text.bodySmall?.copyWith(color: colors.mutedForeground)
                      : text.bodyMedium,
                ),
              ),
            ],
          ),
          if (unlocked == null) ...[
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: onWatchAd,
              icon: const Icon(LucideIcons.play, size: 16),
              label: Text('hint.watch_ad'.tr()),
            ),
          ],
        ],
      ),
    );
  }
}
