import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AppColors (OVERRIDES §2 토큰)', () {
    test('라이트/다크가 OVERRIDES 표의 값을 그대로 쓴다', () {
      expect(AppColors.light.background, const Color(0xFFFAFAF9));
      expect(AppColors.light.foreground, const Color(0xFF0F172A));
      expect(AppColors.light.primaryButton, const Color(0xFF0F172A));
      expect(AppColors.light.onPrimaryButton, const Color(0xFFFFFFFF));
      expect(AppColors.light.brand, const Color(0xFFEA580C));
      expect(AppColors.light.tileCorrect, const Color(0xFF16A34A));
      expect(AppColors.light.tileEmpty, AppColors.light.muted);

      expect(AppColors.dark.background, const Color(0xFF141A26));
      expect(AppColors.dark.foreground, const Color(0xFFF1F5F9));
      expect(AppColors.dark.primaryButton, const Color(0xFFF1F5F9));
      expect(AppColors.dark.onPrimaryButton, const Color(0xFF141A26));
      expect(AppColors.dark.brand, const Color(0xFFF97316));
      expect(AppColors.dark.tileCorrect, const Color(0xFF22C55E));
      expect(AppColors.dark.tileEmpty, AppColors.dark.muted);
    });

    // OVERRIDES §2: 다크에서 밝은 타일 글자는 대비 위반(2.8:1)이라 금지.
    test('타일 글자색은 다크에서 어둡다', () {
      expect(AppColors.light.tileTextOnCorrect, const Color(0xFFFFFFFF));
      expect(AppColors.dark.tileTextOnCorrect, const Color(0xFF052E16));
    });
  });

  group('appTheme', () {
    test('brand 를 면이나 글자색으로 쓰지 않는다 (OVERRIDES §2)', () {
      for (final brightness in Brightness.values) {
        final theme = appTheme(brightness);
        final colors = AppColors.of(brightness);

        expect(theme.colorScheme.primary, isNot(colors.brand));
        expect(
          theme.filledButtonTheme.style?.backgroundColor?.resolve({}),
          colors.primaryButton,
        );
        expect(theme.textTheme.bodyMedium?.color, colors.foreground);
      }
    });

    test('화면 배경·본문 색이 토큰과 같다', () {
      expect(
        appTheme(Brightness.light).scaffoldBackgroundColor,
        AppColors.light.background,
      );
      expect(
        appTheme(Brightness.dark).scaffoldBackgroundColor,
        AppColors.dark.background,
      );
    });

    test('그림자가 없다 (OVERRIDES §4)', () {
      for (final brightness in Brightness.values) {
        final theme = appTheme(brightness);
        expect(theme.appBarTheme.elevation, 0);
        expect(theme.appBarTheme.scrolledUnderElevation, 0);
        expect(theme.bottomNavigationBarTheme.elevation, 0);
        expect(theme.navigationBarTheme.elevation, 0);
        expect(theme.filledButtonTheme.style?.elevation?.resolve({}), 0);
        expect(theme.bottomSheetTheme.elevation, 0);
        expect(theme.shadowColor, Colors.transparent);
      }
    });

    test('Pretendard 를 쓰고 Inter 로 폴백한다 (OVERRIDES §3)', () {
      final theme = appTheme(Brightness.light);

      expect(theme.textTheme.bodyMedium?.fontFamily, 'Pretendard');
      expect(theme.textTheme.bodyMedium?.fontFamilyFallback, contains('Inter'));
    });

    test('본문 크기 16, line-height 1.5 (OVERRIDES §3)', () {
      final body = appTheme(Brightness.light).textTheme.bodyMedium!;

      expect(body.fontSize, 16);
      expect(body.height, 1.5);
    });

    test('버튼 모서리 10, 바텀시트 20 (OVERRIDES §4)', () {
      final theme = appTheme(Brightness.light);
      final buttonShape =
          theme.filledButtonTheme.style!.shape!.resolve({})!
              as RoundedRectangleBorder;

      expect(buttonShape.borderRadius, BorderRadius.circular(10));
      expect(
        theme.bottomSheetTheme.shape,
        const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
      );
    });

    // OVERRIDES §4 는 44(iOS HIG), Material 은 48 을 요구한다 — 둘 다 만족한다.
    test('터치 타깃이 44·48 을 모두 넘는다', () {
      final theme = appTheme(Brightness.light);

      for (final style in [
        theme.filledButtonTheme.style,
        theme.outlinedButtonTheme.style,
        theme.textButtonTheme.style,
      ]) {
        expect(
          style?.minimumSize?.resolve({})?.height,
          greaterThanOrEqualTo(48),
        );
      }
    });

    test('ThemeExtension 으로 게임 피드백 색을 꺼낼 수 있다', () {
      final light = appTheme(Brightness.light).extension<AppColors>();
      final dark = appTheme(Brightness.dark).extension<AppColors>();

      expect(light, AppColors.light);
      expect(dark, AppColors.dark);
    });
  });
}
