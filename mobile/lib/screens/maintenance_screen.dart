import 'package:chosung/startup/startup_state.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/widgets/max_width_body.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// S7 점검 화면. 목업이 없어서 SCREENS 명세(아이콘 + 제목 + 예상 시각)와
/// OVERRIDES 토큰만으로 만들었다.
class MaintenanceScreen extends StatelessWidget {
  const MaintenanceScreen({required this.state, super.key});

  final StartupMaintenance state;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;

    return Scaffold(
      body: SafeArea(
        child: MaxWidthBody(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  LucideIcons.wrench,
                  size: 32,
                  color: colors.mutedForeground,
                ),
                const SizedBox(height: 16),
                Text('maintenance.title'.tr(), style: text.headlineMedium),
                const SizedBox(height: 8),
                Text(
                  // 운영자가 메시지를 안 넣었으면 기본 안내를 쓴다.
                  state.message ?? 'maintenance.fallback'.tr(),
                  style: text.bodyMedium?.copyWith(
                    color: colors.mutedForeground,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
