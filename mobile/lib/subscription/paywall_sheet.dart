import 'dart:async';

import 'package:chosung/analytics/analytics_event.dart';
import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/layout/adaptive_sheet.dart';
import 'package:chosung/settings/legal_links.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:chosung/subscription/purchase_controller.dart';
import 'package:chosung/subscription/subscription_state.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// 테스트와 화면이 같이 쓰는 손잡이. 자동 갱신 고지의 **필수 요소 6개**
/// (`docs/legal-checklist.md` "4. 스토어 정책(구독 고지)": 상품명·기간·가격·
/// 자동 갱신·해지 방법·약관/방침 링크)는 키로 하나씩 못 박아 둔다 — 문구를
/// 다듬다가 한 줄이 사라지면 심사에서 걸린다.
abstract final class PaywallKeys {
  static const productName = Key('paywall.notice.product_name');
  static const period = Key('paywall.notice.period');
  static const price = Key('paywall.notice.price');
  static const autoRenew = Key('paywall.notice.auto_renew');
  static const cancelHow = Key('paywall.notice.cancel_how');
  static const legalLinks = Key('paywall.notice.legal_links');

  static const start = Key('paywall.start');
  static const restore = Key('paywall.restore');
  static const error = Key('paywall.error');

  /// 구독이 확인된 뒤의 얼굴(구매·복원 성공 둘 다 여기로 온다).
  static const entitled = Key('paywall.entitled');
}

/// S5 Paywall 을 띄운다. compact 는 바텀시트, medium 이상은 가운데
/// 다이얼로그(SCREENS T2) — 그 판정은 [showAdaptiveSheet] 한 곳에만 있다.
Future<void> showPaywallSheet({required BuildContext context}) =>
    showAdaptiveSheet<void>(
      context: context,
      builder: (context) => const PaywallSheet(),
    );

/// S5 구독 화면. 가격은 **스토어가 알려준 현지화 문자열**이고 상수가 아니다
/// (스펙 §A.8) — 가격을 못 읽으면 구매 버튼을 잠근다.
class PaywallSheet extends ConsumerStatefulWidget {
  const PaywallSheet({super.key});

  @override
  ConsumerState<PaywallSheet> createState() => _PaywallSheetState();
}

class _PaywallSheetState extends ConsumerState<PaywallSheet> {
  @override
  void initState() {
    super.initState();
    // 진입 이벤트는 열릴 때 한 번이다(스펙 "미정 항목" 20).
    unawaited(ref.read(analyticsServiceProvider).log(paywallViewEvent));
    // 시작 때 조회가 실패했으면(네트워크·스토어) 여기서 한 번 더 읽는다 —
    // 가격이 없으면 구매 자체가 막히는 화면이라 재시도 자리가 필요하다.
    if (ref.read(purchaseFlowProvider).product == null) {
      unawaited(ref.read(purchaseFlowProvider.notifier).loadProduct());
    }
  }

  @override
  Widget build(BuildContext context) {
    final phase = ref.watch(subscriptionPhaseProvider);
    final entitled =
        phase == SubscriptionPhase.active || phase == SubscriptionPhase.grace;

    return SafeArea(
      // 바텀시트는 `isScrollControlled` 라 높이 제한이 없다 — 혜택·고지를 다
      // 담으면 폰 화면보다 길어져서 링크가 화면 밖으로 나간다. 높이를 묶고
      // 안쪽을 스크롤한다(다이얼로그 쪽은 [Dialog] 가 이미 묶어 준다).
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.9,
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: entitled
                ? [_EntitledBody(phase: phase)]
                : const [_OfferBody()],
          ),
        ),
      ),
    );
  }
}

/// 구독이 확인된 뒤. 구매 직후와 "구매 복원" 성공이 같은 얼굴을 쓴다 — 둘의
/// 결과가 같기 때문이다(권한이 들어왔다).
class _EntitledBody extends ConsumerWidget {
  const _EntitledBody({required this.phase});

  final SubscriptionPhase phase;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final until = ref.watch(entitlementProvider)?.until;
    final grace = phase == SubscriptionPhase.grace;

    return Column(
      key: PaywallKeys.entitled,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Semantics(
          header: true,
          child: Text(
            grace
                ? 'subscription.grace_title'.tr()
                : 'subscription.active_title'.tr(),
            style: text.titleMedium,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          (grace ? 'subscription.grace_body' : 'subscription.active_body').tr(
            namedArgs: {'date': entitlementDateLabel(context, until)},
          ),
          style: text.bodySmall?.copyWith(color: colors.mutedForeground),
        ),
        const SizedBox(height: 24),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text('subscription.close'.tr()),
        ),
      ],
    );
  }
}

class _OfferBody extends ConsumerWidget {
  const _OfferBody();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final flow = ref.watch(purchaseFlowProvider);
    final phase = ref.watch(subscriptionPhaseProvider);
    final notifier = ref.read(purchaseFlowProvider.notifier);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Semantics(
          header: true,
          child: Text('subscription.title'.tr(), style: text.headlineSmall),
        ),
        const SizedBox(height: 4),
        Text(
          'subscription.subtitle'.tr(),
          style: text.bodyMedium?.copyWith(color: colors.mutedForeground),
        ),
        const SizedBox(height: 24),
        // 혜택 3줄(SCREENS S5). 가운데 줄 문구는 스펙 §B.21 이 못 박았다.
        for (final benefit in const [
          'subscription.benefit_ads',
          'subscription.benefit_hint',
          'subscription.benefit_devices',
        ])
          _Benefit(label: benefit.tr()),
        const SizedBox(height: 24),
        const _PriceCard(),
        const SizedBox(height: 24),
        FilledButton(
          key: PaywallKeys.start,
          // 가격을 모르면(=상품 조회 실패) 결제 창을 띄우지 않는다. 결제·검증·
          // 복원이 도는 동안에도 잠근다 — 두 번 누르면 거래가 두 개 생긴다.
          onPressed: flow.product == null || flow.busy
              ? null
              : () => unawaited(notifier.start()),
          child: Text(
            // pending·verifying 은 사용자에게 같은 일이다("결제 확인 중").
            flow.busy && phase != SubscriptionPhase.error
                ? 'subscription.verifying'.tr()
                : 'subscription.start'.tr(),
          ),
        ),
        const SizedBox(height: 4),
        TextButton(
          key: PaywallKeys.restore,
          onPressed: flow.busy ? null : () => unawaited(notifier.restore()),
          child: Text(
            flow.restoring
                ? 'subscription.restoring'.tr()
                : 'subscription.restore'.tr(),
          ),
        ),
        if (flow.error case final error?) ...[
          const SizedBox(height: 8),
          Text(
            key: PaywallKeys.error,
            error.tr(),
            textAlign: TextAlign.center,
            style: text.bodySmall?.copyWith(color: colors.destructive),
          ),
        ],
        const SizedBox(height: 16),
        const _LegalLinks(),
      ],
    );
  }
}

class _Benefit extends StatelessWidget {
  const _Benefit({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          // 체크는 장식이다 — 문구가 혜택을 다 말하므로 스크린 리더는 아이콘을
          // 읽지 않아도 된다.
          ExcludeSemantics(
            child: Icon(LucideIcons.check, size: 18, color: colors.brand),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(label, style: Theme.of(context).textTheme.bodyLarge),
          ),
        ],
      ),
    );
  }
}

/// 가격 카드 = 자동 갱신 고지의 상품명·기간·가격이 모여 있는 자리.
class _PriceCard extends ConsumerWidget {
  const _PriceCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final product = ref.watch(purchaseFlowProvider).product;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border.all(color: colors.brand),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            key: PaywallKeys.productName,
            'subscription.product_name'.tr(),
            style: text.labelLarge,
          ),
          const SizedBox(height: 4),
          Text(
            key: PaywallKeys.price,
            // 스토어 현지화 가격 그대로. 상수(₩1,500)로 박지 않는다.
            product?.price ?? 'subscription.price_loading'.tr(),
            style: text.titleLarge,
          ),
          const SizedBox(height: 4),
          Text(
            key: PaywallKeys.period,
            'subscription.period'.tr(),
            style: text.bodySmall?.copyWith(color: colors.mutedForeground),
          ),
          const SizedBox(height: 8),
          Text(
            key: PaywallKeys.autoRenew,
            'subscription.auto_renew'.tr(),
            style: text.bodySmall?.copyWith(color: colors.mutedForeground),
          ),
          const SizedBox(height: 4),
          Text(
            key: PaywallKeys.cancelHow,
            'subscription.cancel_how'.tr(),
            style: text.bodySmall?.copyWith(color: colors.mutedForeground),
          ),
        ],
      ),
    );
  }
}

/// 약관·개인정보처리방침(애플 필수). S4 설정과 같은 URL 규칙을 쓴다.
class _LegalLinks extends ConsumerWidget {
  const _LegalLinks();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final uiLanguage = Localizations.localeOf(context).languageCode;
    final open = ref.read(webLinkLauncherProvider);

    // 긴 영문 라벨("Terms of service · Privacy policy")이 좁은 폭에서 두 줄로
    // 접히게 Wrap 이다 — Row 면 넘쳐서 글자가 잘린다.
    return Wrap(
      key: PaywallKeys.legalLinks,
      alignment: WrapAlignment.center,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        // 순서는 SCREENS S5 하단 링크 그대로("이용약관 · 개인정보처리방침").
        for (final document in const [
          LegalDocument.terms,
          LegalDocument.privacy,
        ]) ...[
          if (document != LegalDocument.terms)
            Text('·', style: text.bodySmall?.copyWith(color: colors.border)),
          TextButton(
            onPressed: () => open(
              legalDocumentUrl(document: document, uiLanguage: uiLanguage),
            ),
            child: Text(
              'subscription.${document.path}'.tr(),
              style: text.bodySmall?.copyWith(color: colors.mutedForeground),
            ),
          ),
        ],
      ],
    );
  }
}

/// 권한 시각을 기기 로컬 날짜로 그린다. 서버는 UTC 로 보내므로
/// ([Entitlement] 참고) 여기서만 [DateTime.toLocal] 을 거친다.
String entitlementDateLabel(BuildContext context, DateTime? until) =>
    until == null
    ? '—'
    : DateFormat.yMMMd(
        Localizations.localeOf(context).toLanguageTag(),
      ).format(until.toLocal());
