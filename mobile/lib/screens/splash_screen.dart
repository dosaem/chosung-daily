import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/widgets/skeleton_box.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// 시작 흐름이 도는 동안의 화면. 실패하면 같은 자리에서 인라인 카드 +
/// 재시도 버튼을 보여준다 — 토스트로 숨기지 않는다(OVERRIDES §7).
class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final startup = ref.watch(startupProvider);

    return Scaffold(
      body: SafeArea(
        child: ReadingWidth(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: startup.hasError
                ? _StartupError(
                    onRetry: ref.read(startupProvider.notifier).retry,
                  )
                : const _StartupSkeleton(),
          ),
        ),
      ),
    );
  }
}

class _StartupSkeleton extends StatelessWidget {
  const _StartupSkeleton();

  @override
  Widget build(BuildContext context) => Column(
    mainAxisAlignment: MainAxisAlignment.center,
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text('app.name'.tr(), style: Theme.of(context).textTheme.headlineMedium),
      const SizedBox(height: 24),
      const SkeletonBox(height: 48, width: 240),
      const SizedBox(height: 12),
      const SkeletonBox(height: 16, width: 120),
    ],
  );
}

class _StartupError extends StatelessWidget {
  const _StartupError({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(LucideIcons.wifiOff, color: colors.mutedForeground),
        const SizedBox(height: 12),
        Text('startup.error_title'.tr(), style: text.titleLarge),
        const SizedBox(height: 4),
        Text(
          'startup.error_body'.tr(),
          style: text.bodyMedium?.copyWith(color: colors.mutedForeground),
        ),
        const SizedBox(height: 24),
        FilledButton(onPressed: onRetry, child: Text('startup.retry'.tr())),
      ],
    );
  }
}
