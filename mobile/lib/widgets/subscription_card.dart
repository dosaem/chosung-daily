import 'dart:async';

import 'package:chosung/settings/legal_links.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:chosung/subscription/paywall_sheet.dart';
import 'package:chosung/subscription/purchase_controller.dart';
import 'package:chosung/subscription/subscription_state.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/widgets/settings_row.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// S4 구독 카드. 세 얼굴뿐이다(SCREENS S4):
/// 미구독 → Paywall, 구독 중 → "광고 제거 · 갱신일", 유예 중 → "결제 확인 중 ·
/// 유예 …까지" + "관리"(스토어로).
///
/// 어느 얼굴인지는 [subscriptionPhaseProvider] 가 정한다 — 이 위젯이 권한·
/// 구매 상태를 다시 조합하면 Paywall 과 다른 답을 낼 수 있다.
class SubscriptionCard extends ConsumerWidget {
  const SubscriptionCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final phase = ref.watch(subscriptionPhaseProvider);

    return switch (phase) {
      SubscriptionPhase.active || SubscriptionPhase.grace => _EntitledRow(
        grace: phase == SubscriptionPhase.grace,
      ),
      // 결제·검증이 도는 동안에도 Paywall 을 열 수 있다 — 거기에 진행 상황과
      // 실패 사유가 있다.
      _ => const _OfferRow(),
    };
  }
}

class _OfferRow extends ConsumerWidget {
  const _OfferRow();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final flow = ref.watch(purchaseFlowProvider);
    final price = flow.product?.price;

    final String value;
    if (flow.busy) {
      // 결제가 떠 있으면 그걸 먼저 말한다 — 가격 안내는 지금 할 말이 아니다.
      value = 'subscription.verifying'.tr();
    } else if (price == null) {
      // 가격을 못 읽었으면 금액 없이 안내만 한다 — ₩1,500 은 한국 Tier
      // 설정값일 뿐이라 앱이 대신 적을 수 없다(스펙 §A.8).
      value = 'subscription.card_idle_no_price'.tr();
    } else {
      value = 'subscription.card_idle'.tr(namedArgs: {'price': price});
    }

    return SettingsRow(
      label: 'records.subscription'.tr(),
      value: value,
      onTap: () => unawaited(showPaywallSheet(context: context)),
    );
  }
}

class _EntitledRow extends ConsumerWidget {
  const _EntitledRow({required this.grace});

  final bool grace;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final entitlement = ref.watch(entitlementProvider);
    final date = entitlementDateLabel(context, entitlement?.until);
    final open = ref.read(webLinkLauncherProvider);
    // 어느 스토어에서 온 권한인지는 서버가 알려준다 — 기기 플랫폼으로 고르면
    // 복원으로 다른 스토어 구독을 이어받은 경우에 엉뚱한 앱이 열린다.
    final store = entitlement?.source;

    // 설정 행(한 줄)이 아니라 두 줄이다 — "광고 제거 · 2026. 10. 31. 갱신" 과
    // "관리" 는 폰 폭에서 한 줄에 들어가지 않는다.
    return ConstrainedBox(
      constraints: const BoxConstraints(minHeight: SettingsRow.minHeight),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 12),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'records.subscription'.tr(),
                    style: text.bodyMedium?.copyWith(color: colors.foreground),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    (grace
                            ? 'subscription.card_grace'
                            : 'subscription.card_active')
                        .tr(namedArgs: {'date': date}),
                    style: text.bodySmall?.copyWith(
                      color: colors.mutedForeground,
                    ),
                  ),
                ],
              ),
            ),
            if (store != null)
              TextButton(
                key: manageSubscriptionKey,
                onPressed: () => open(subscriptionManagementUrl(store)),
                child: Text('subscription.manage'.tr()),
              ),
          ],
        ),
      ),
    );
  }
}

const manageSubscriptionKey = Key('records.subscription.manage');
