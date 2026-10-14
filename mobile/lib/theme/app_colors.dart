import 'package:flutter/material.dart';

/// `design-system/hidden-vowels/OVERRIDES.md` §2 의 색 토큰.
///
/// 토큰 이름을 그대로 필드 이름으로 쓴다 — 디자인 문서와 코드를 대조할 때
/// 중간 번역이 없게 하려는 선택이다. `ColorScheme` 에 자리가 없는 게임 피드백
/// 색까지 한 곳에 모으려고 [ThemeExtension] 으로 만들었다.
@immutable
class AppColors extends ThemeExtension<AppColors> {
  const AppColors({
    required this.brand,
    required this.primaryButton,
    required this.onPrimaryButton,
    required this.brandSubtle,
    required this.background,
    required this.foreground,
    required this.card,
    required this.muted,
    required this.mutedForeground,
    required this.border,
    required this.destructive,
    required this.tileCorrect,
    required this.tileWrong,
    required this.tileTextOnCorrect,
  });

  /// 불꽃 아이콘·활성 탭 밑줄·포커스 링·선택 칩 테두리 전용.
  /// 면 채움 금지, 일반 크기 글자색 금지(라이트에서 AA 미달).
  final Color brand;
  final Color primaryButton;
  final Color onPrimaryButton;
  final Color brandSubtle;
  final Color background;
  final Color foreground;
  final Color card;
  final Color muted;
  final Color mutedForeground;
  final Color border;
  final Color destructive;

  /// 위치·글자 모두 일치(🟩).
  final Color tileCorrect;

  /// 불일치(⬜). 글자는 [foreground].
  final Color tileWrong;

  /// 타일 글자는 28pt+ bold 라 large text 기준 3:1 을 적용한다.
  final Color tileTextOnCorrect;

  /// 아직 입력하지 않은 칸. 테두리 없이 면만 — 토큰 값은 [muted] 와 같다.
  Color get tileEmpty => muted;

  static const light = AppColors(
    brand: Color(0xFFEA580C),
    primaryButton: Color(0xFF0F172A),
    onPrimaryButton: Color(0xFFFFFFFF),
    brandSubtle: Color(0xFFFFF7ED),
    background: Color(0xFFFAFAF9),
    foreground: Color(0xFF0F172A),
    card: Color(0xFFFFFFFF),
    muted: Color(0xFFF5F5F4),
    mutedForeground: Color(0xFF57534E),
    border: Color(0xFFE7E5E4),
    destructive: Color(0xFFDC2626),
    tileCorrect: Color(0xFF16A34A),
    tileWrong: Color(0xFFD6D3D1),
    tileTextOnCorrect: Color(0xFFFFFFFF),
  );

  static const dark = AppColors(
    brand: Color(0xFFF97316),
    primaryButton: Color(0xFFF1F5F9),
    onPrimaryButton: Color(0xFF141A26),
    brandSubtle: Color(0xFF431407),
    background: Color(0xFF141A26),
    foreground: Color(0xFFF1F5F9),
    card: Color(0xFF1C2433),
    muted: Color(0xFF253044),
    mutedForeground: Color(0xFF94A3B8),
    border: Color(0xFF2A3447),
    destructive: Color(0xFFEF4444),
    tileCorrect: Color(0xFF22C55E),
    tileWrong: Color(0xFF475569),
    tileTextOnCorrect: Color(0xFF052E16),
  );

  static AppColors of(Brightness brightness) =>
      brightness == Brightness.dark ? dark : light;

  /// 화면에서 쓰는 통로: `AppColors.from(context)`.
  static AppColors from(BuildContext context) =>
      Theme.of(context).extension<AppColors>() ??
      of(Theme.of(context).brightness);

  @override
  AppColors copyWith() => this;

  /// 라이트↔다크는 시스템 설정이 바뀔 때 한 번에 갈린다 — 색을 섞을 자리가 없다.
  @override
  AppColors lerp(AppColors? other, double t) =>
      t < 0.5 ? this : (other ?? this);
}
