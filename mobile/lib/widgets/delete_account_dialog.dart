import 'package:chosung/layout/adaptive_sheet.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';

/// 계정 삭제 확인(US 22). 폭에 따라 바텀시트/다이얼로그다(SCREENS T2).
///
/// 삭제를 고르면 true. **여기서 지우지 않는다** — 지우는 건 부른 쪽이고,
/// 이 위젯은 "되돌릴 수 없음" 과 "구독은 따로 해지" 를 말하는 일만 한다.
Future<bool?> showDeleteAccountDialog({required BuildContext context}) =>
    showAdaptiveSheet<bool>(
      context: context,
      builder: (context) => const DeleteAccountConfirm(),
    );

class DeleteAccountConfirm extends StatelessWidget {
  const DeleteAccountConfirm({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Semantics(
              header: true,
              child: Text(
                'account.delete_title'.tr(),
                style: text.titleMedium,
              ),
            ),
            const SizedBox(height: 8),
            Text('account.delete_body'.tr(), style: text.bodySmall),
            const SizedBox(height: 24),
            // 되돌릴 수 없는 쪽을 기본값으로 두지 않는다 — 취소가 먼저고,
            // 삭제는 destructive 색 글자다(OVERRIDES §2).
            OutlinedButton(
              key: deleteAccountCancelKey,
              onPressed: () => Navigator.of(context).pop(false),
              child: Text('account.delete_cancel'.tr()),
            ),
            const SizedBox(height: 8),
            TextButton(
              key: deleteAccountConfirmKey,
              onPressed: () => Navigator.of(context).pop(true),
              style: TextButton.styleFrom(foregroundColor: colors.destructive),
              child: Text('account.delete_confirm'.tr()),
            ),
          ],
        ),
      ),
    );
  }
}

const deleteAccountCancelKey = Key('account.delete.cancel');
const deleteAccountConfirmKey = Key('account.delete.confirm');
