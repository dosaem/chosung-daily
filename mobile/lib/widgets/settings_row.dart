import 'package:chosung/theme/app_colors.dart';
import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// S4 설정 리스트의 한 줄. 라벨(좌) + 현재 값(우) + 누를 수 있으면 화살표.
///
/// [onTap] 이 null 이면 아직 아무 일도 하지 않는 자리다 — 뒤 티켓(28~32)이
/// 채운다. 비활성은 색으로만 말하지 않고 화살표를 빼서 같이 알린다.
class SettingsRow extends StatelessWidget {
  const SettingsRow({
    required this.label,
    super.key,
    this.value,
    this.onTap,
    this.trailing,
    this.destructive = false,
  });

  /// 터치 타깃 최소 44(OVERRIDES §4).
  static const minHeight = 44.0;

  final String label;
  final String? value;
  final VoidCallback? onTap;

  /// 값 대신 놓는 조작 위젯(리마인더 on/off 스위치, 티켓 30). 스스로 탭을 먹는
  /// 위젯이라 그 행의 [onTap] 은 비워 둔다 — 행을 눌러도, 스위치를 눌러도
  /// 같은 일이 벌어지게 만들면 "껐는데 다시 켜졌다" 가 생긴다.
  final Widget? trailing;

  /// 계정 삭제처럼 되돌릴 수 없는 행(OVERRIDES §2 `destructive`).
  final bool destructive;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final enabled = onTap != null;
    final labelColor = destructive
        ? colors.destructive
        : (enabled ? colors.foreground : colors.mutedForeground);

    return InkWell(
      onTap: onTap,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: minHeight),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 12),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: text.bodyMedium?.copyWith(color: labelColor),
                ),
              ),
              if (value case final value?) ...[
                const SizedBox(width: 12),
                Text(
                  value,
                  style: text.bodySmall?.copyWith(
                    color: colors.mutedForeground,
                  ),
                ),
              ],
              if (trailing case final trailing?) ...[
                const SizedBox(width: 8),
                trailing,
              ],
              if (enabled) ...[
                const SizedBox(width: 4),
                Icon(
                  LucideIcons.chevronRight,
                  size: 16,
                  color: colors.mutedForeground,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
