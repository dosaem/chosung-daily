import 'package:chosung/theme/app_colors.dart';
import 'package:flutter/material.dart';

/// OVERRIDES §3. 번들 폰트가 없는 환경(테스트·웹 프리뷰)에서는 Inter → system.
const _fontFamily = 'Pretendard';
const _fontFamilyFallback = ['Inter'];

/// OVERRIDES §4 모서리.
const _tileRadius = 8.0;
const _buttonRadius = 10.0;
const _cardRadius = 16.0;
const _sheetRadius = 20.0;

/// OVERRIDES §4 는 최소 44×44(iOS HIG 기준)를 요구하고, Material 은 48×48 을
/// 요구한다 — 둘 다 만족하는 48 로 둔다.
const _minTouchTarget = 48.0;

ThemeData appTheme(Brightness brightness) {
  final colors = AppColors.of(brightness);

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    extensions: [colors],
    colorScheme: _colorScheme(brightness, colors),
    scaffoldBackgroundColor: colors.background,
    canvasColor: colors.background,
    // OVERRIDES §4: 그림자 없음. 섹션 구분은 헤어라인 1px 과 여백으로만.
    shadowColor: Colors.transparent,
    textTheme: _textTheme(colors),
    fontFamily: _fontFamily,
    fontFamilyFallback: _fontFamilyFallback,
    dividerTheme: DividerThemeData(
      color: colors.border,
      thickness: 1,
      space: 1,
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: colors.background,
      foregroundColor: colors.foreground,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: colors.background,
      indicatorColor: Colors.transparent,
      elevation: 0,
      surfaceTintColor: Colors.transparent,
      labelTextStyle: WidgetStatePropertyAll(
        TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: colors.foreground,
        ),
      ),
    ),
    bottomNavigationBarTheme: BottomNavigationBarThemeData(
      backgroundColor: colors.background,
      selectedItemColor: colors.foreground,
      unselectedItemColor: colors.mutedForeground,
      elevation: 0,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: ButtonStyle(
        backgroundColor: WidgetStatePropertyAll(colors.primaryButton),
        foregroundColor: WidgetStatePropertyAll(colors.onPrimaryButton),
        elevation: const WidgetStatePropertyAll(0),
        minimumSize: const WidgetStatePropertyAll(Size(0, _minTouchTarget)),
        shape: WidgetStatePropertyAll(
          RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(_buttonRadius),
          ),
        ),
        // 글꼴을 여기서도 적어준다 — ButtonStyle 의 textStyle 은 ThemeData 의
        // textTheme 을 거치지 않아서, 비워 두면 주 버튼 글자만 시스템 글꼴로
        // 나온다(OVERRIDES §3 은 UI 전체를 Pretendard 로 둔다).
        textStyle: const WidgetStatePropertyAll(
          TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            fontFamily: _fontFamily,
            fontFamilyFallback: _fontFamilyFallback,
          ),
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: ButtonStyle(
        foregroundColor: WidgetStatePropertyAll(colors.foreground),
        side: WidgetStatePropertyAll(BorderSide(color: colors.border)),
        minimumSize: const WidgetStatePropertyAll(Size(0, _minTouchTarget)),
        shape: WidgetStatePropertyAll(
          RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(_buttonRadius),
          ),
        ),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: ButtonStyle(
        foregroundColor: WidgetStatePropertyAll(colors.foreground),
        minimumSize: const WidgetStatePropertyAll(Size(0, _minTouchTarget)),
      ),
    ),
    cardTheme: CardThemeData(
      color: colors.card,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(_cardRadius),
      ),
    ),
    bottomSheetTheme: BottomSheetThemeData(
      backgroundColor: colors.card,
      elevation: 0,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(_sheetRadius)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: colors.muted,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(_tileRadius),
        borderSide: BorderSide.none,
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(_tileRadius),
        // brand 는 테두리·포커스 링에만 쓴다.
        borderSide: BorderSide(color: colors.brand, width: 2),
      ),
    ),
    progressIndicatorTheme: ProgressIndicatorThemeData(
      color: colors.foreground,
    ),
  );
}

/// Material 의 `primary` 는 면 채움에 쓰이므로 `brand`(오렌지)를 넣지 않는다 —
/// OVERRIDES §2 가 brand 면 채움·글자색을 금지한다. 주 버튼 색을 넣는다.
ColorScheme _colorScheme(Brightness brightness, AppColors colors) =>
    ColorScheme(
      brightness: brightness,
      primary: colors.primaryButton,
      onPrimary: colors.onPrimaryButton,
      secondary: colors.foreground,
      onSecondary: colors.background,
      surface: colors.background,
      onSurface: colors.foreground,
      surfaceContainerHighest: colors.muted,
      onSurfaceVariant: colors.mutedForeground,
      outline: colors.border,
      outlineVariant: colors.border,
      error: colors.destructive,
      onError: Colors.white,
    );

/// OVERRIDES §3 스케일 12 / 14 / 16(기본) / 20 / 24 / 32, 본문 line-height 1.5.
TextTheme _textTheme(AppColors colors) {
  TextStyle style(double size, FontWeight weight, {double height = 1.5}) =>
      TextStyle(
        fontSize: size,
        fontWeight: weight,
        height: height,
        color: colors.foreground,
        // 한글 자간 -0.01em.
        letterSpacing: size * -0.01,
      );

  return TextTheme(
    displaySmall: style(32, FontWeight.w700, height: 1.2),
    headlineMedium: style(24, FontWeight.w700, height: 1.3),
    titleLarge: style(20, FontWeight.w600, height: 1.4),
    titleMedium: style(16, FontWeight.w600),
    bodyMedium: style(16, FontWeight.w400),
    bodySmall: style(14, FontWeight.w400),
    labelSmall: style(
      12,
      FontWeight.w400,
    ).copyWith(color: colors.mutedForeground),
  );
}
