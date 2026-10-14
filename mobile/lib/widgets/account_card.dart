import 'dart:async';

import 'package:chosung/account/account_controller.dart';
import 'package:chosung/account/social_sign_in.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/records/my_stats_controller.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// OVERRIDES §6 `AccountCard` — S4 의 계정 자리(목업 `e4_records`).
///
/// 미연결이면 연결 버튼(Android 는 구글만, 스펙 §A.6 표), 연결됐으면 provider
/// 이름 + 마스킹 이메일 한 줄이다. 실패는 카드 아래 한 줄로 말한다 —
/// 토스트로 흘려보내지 않는다(OVERRIDES §7).
class AccountCard extends ConsumerWidget {
  const AccountCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final account = ref.watch(accountProvider);
    final linked = ref.watch(myStatsProvider).value?.linkedAccount;
    // 이 카드는 연결 버튼이 시작한 일만 말한다 — 백업 코드 시트·삭제
    // 다이얼로그의 오류는 각자의 자리에 있다.
    final error = account.errorFor(_linkActions);
    final busy = account.isRunning(_linkActions);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (linked != null)
            _LinkedAccount(account: linked, switched: account.switched)
          else
            const _LinkButtons(),
          if (busy)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'account.working'.tr(),
                style: text.bodySmall?.copyWith(color: colors.mutedForeground),
              ),
            ),
          if (error case final error?)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                error.tr(),
                style: text.bodySmall?.copyWith(color: colors.destructive),
              ),
            ),
        ],
      ),
    );
  }
}

/// 연결됨. 목업 `e4_records` 의 "Google · hs***@gmail.com 연결됨" + 보조 한 줄.
class _LinkedAccount extends StatelessWidget {
  const _LinkedAccount({required this.account, required this.switched});

  final LinkedAccount account;
  final bool switched;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final provider = providerDisplayName(account.provider);
    final title = switch (account.email) {
      final String email => 'account.linked'.tr(
        namedArgs: {'provider': provider, 'email': maskEmail(email)},
      ),
      // 애플은 이메일 공유를 거부할 수 있다 — provider 만 말한다.
      null => 'account.linked_no_email'.tr(namedArgs: {'provider': provider}),
    };

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Icon(
            providerIcon(account.provider),
            size: 16,
            color: colors.brand,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: text.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 2),
              Text(
                (switched ? 'account.switched' : 'account.description').tr(),
                style: text.bodySmall?.copyWith(color: colors.mutedForeground),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// 미연결. iOS 는 구글·애플 둘, Android 는 구글만이다 — Android 애플 로그인은
/// Out of Scope 고, 애플 계정 기록은 백업 코드로 옮긴다(US 18a).
class _LinkButtons extends ConsumerWidget {
  const _LinkButtons();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = AppColors.from(context);
    final busy = ref.watch(accountProvider).busy;
    final notifier = ref.read(accountProvider.notifier);
    final buttons = [
      (
        key: accountLinkGoogleKey,
        label: 'account.link_google'.tr(),
        provider: AccountProvider.google,
      ),
      if (ref.watch(isIosProvider))
        (
          key: accountLinkAppleKey,
          label: 'account.link_apple'.tr(),
          provider: AccountProvider.apple,
        ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'account.description'.tr(),
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: colors.mutedForeground),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            for (final button in buttons) ...[
              if (button != buttons.first) const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton(
                  key: button.key,
                  onPressed: busy
                      ? null
                      : () => unawaited(notifier.link(button.provider)),
                  child: Text(button.label),
                ),
              ),
            ],
          ],
        ),
      ],
    );
  }
}

/// 계정 카드가 책임지는 일들.
const Set<AccountAction> _linkActions = {
  AccountAction.linkGoogle,
  AccountAction.linkApple,
};

/// 두 버튼을 테스트와 태블릿 레이아웃이 같이 찾는다.
const accountLinkGoogleKey = Key('account.link.google');
const accountLinkAppleKey = Key('account.link.apple');

/// 서버가 주는 `provider` 문자열을 화면 이름으로. 모르는 값이면 그대로 쓴다 —
/// 서버가 앱보다 먼저 provider 를 늘려도 빈 줄이 되지 않는다.
String providerDisplayName(String provider) => switch (provider) {
  'google' => 'Google',
  'apple' => 'Apple',
  _ => provider,
};

/// provider 아이콘(티켓 29 체크박스 3, SCREENS S4). Lucide 에는 구글·애플
/// 브랜드 마크가 없어 가장 가까운 선 아이콘으로 가른다 — 둘을 같은 아이콘으로
/// 두면 어느 계정이 붙었는지 아이콘이 말해 주지 못한다. 모르는 provider 는
/// [providerDisplayName] 과 같은 이유로 공통 아이콘으로 떨어진다.
/// 연결됨 줄의 provider 아이콘.
///
/// Apple 은 Lucide 의 `apple` 이 그 회사를 가리키는 마크라 그대로 쓴다.
/// Google 은 Lucide 에 대응하는 마크가 없다 — 한때 `chrome` 을 썼지만 그건
/// **브라우저** 브랜드라 구글 계정 표시로 쓰면 다른 제품을 가리키는 것으로
/// 읽힌다(브랜드 오용). 공식 'G' 로고 에셋은 콘솔 등록과 함께 들어오므로
/// (`docs/RELEASE.md` "### 29.") 그때까지는 중립 아이콘으로 두고, provider 는
/// 바로 옆 "Google · …" 텍스트 라벨이 가린다.
IconData providerIcon(String provider) => switch (provider) {
  'apple' => LucideIcons.apple,
  _ => LucideIcons.userCheck,
};
