import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/startup/startup_state.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:url_launcher/url_launcher.dart';

/// 스토어를 연다. 테스트는 이 provider 를 가짜로 덮어 URL 만 확인한다.
final storeLauncherProvider = Provider<Future<void> Function(String url)>(
  (ref) =>
      (url) async =>
          launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication),
);

/// S7 강제 업데이트 화면. 스토어 등록 전에는 `store_urls` 가 null 이라
/// 버튼 없이 안내만 띄운다.
class UpdateRequiredScreen extends ConsumerWidget {
  const UpdateRequiredScreen({required this.state, super.key});

  final StartupUpdateRequired state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final storeUrl = state.storeUrl;

    return Scaffold(
      body: SafeArea(
        child: ReadingWidth(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  LucideIcons.arrowDownCircle,
                  size: 32,
                  color: colors.mutedForeground,
                ),
                const SizedBox(height: 16),
                Text('update.title'.tr(), style: text.headlineMedium),
                const SizedBox(height: 8),
                Text(
                  'update.body'.tr(),
                  style: text.bodyMedium?.copyWith(
                    color: colors.mutedForeground,
                  ),
                ),
                if (storeUrl != null) ...[
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: () => ref.read(storeLauncherProvider)(storeUrl),
                    child: Text('update.open_store'.tr()),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
