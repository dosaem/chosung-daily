import 'package:chosung/theme/app_colors.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// 화면 상단에 붙는 오프라인 줄(OVERRIDES §7). 토스트로 띄우지 않는다 —
/// 연결이 돌아올 때까지 계속 사실이라 한 번 스쳐 보이면 안 된다.
class OfflineBanner extends StatelessWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return DecoratedBox(
      decoration: BoxDecoration(
        color: colors.muted,
        border: Border(bottom: BorderSide(color: colors.border)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            Icon(LucideIcons.wifiOff, size: 16, color: colors.mutedForeground),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'today.offline'.tr(),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: colors.mutedForeground,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
