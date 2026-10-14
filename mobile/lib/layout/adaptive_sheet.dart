import 'package:chosung/layout/app_breakpoint.dart';
import 'package:flutter/material.dart';

abstract final class AdaptiveSheet {
  /// SCREENS T2: 태블릿 다이얼로그 최대 폭.
  static const maxDialogWidth = 560.0;

  /// SCREENS T2: 다이얼로그 상하 여백 최소값.
  static const dialogVerticalInset = 48.0;
}

/// 폭에 따라 바텀시트(compact) 또는 가운데 다이얼로그(medium 이상)로 띄운다.
///
/// 내용 위젯은 하나다 — 26(결과 시트)·29(백업 코드·삭제)·32(Paywall) 가 폭을
/// 신경 쓰지 않고 같은 [builder] 를 넘기면 된다. 1024 폭짜리 화면 아래에 붙은
/// 바텀시트는 잡으려면 손이 너무 멀고, 가로로 늘어난 내용은 읽기 어렵다.
Future<T?> showAdaptiveSheet<T>({
  required BuildContext context,
  required WidgetBuilder builder,
  bool isDismissible = true,
}) {
  if (!AppBreakpoint.of(context).hasRail) {
    return showModalBottomSheet<T>(
      context: context,
      isDismissible: isDismissible,
      enableDrag: isDismissible,
      isScrollControlled: true,
      builder: builder,
    );
  }

  return showDialog<T>(
    context: context,
    barrierDismissible: isDismissible,
    builder: (context) => Dialog(
      insetPadding: const EdgeInsets.symmetric(
        horizontal: 24,
        vertical: AdaptiveSheet.dialogVerticalInset,
      ),
      child: ConstrainedBox(
        constraints: const BoxConstraints(
          maxWidth: AdaptiveSheet.maxDialogWidth,
        ),
        child: builder(context),
      ),
    ),
  );
}
