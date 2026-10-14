import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:chosung/theme/app_colors.dart';
import 'package:flutter_test/flutter_test.dart';

/// 앱 아이콘·스플래시(티켓 35, OVERRIDES §8).
///
/// 아이콘은 생성물(`flutter_launcher_icons`·`flutter_native_splash` 가 만든
/// 네이티브 자산)을 커밋하는 자산이라 analyze·위젯 테스트가 전혀 보지 않는다.
/// 그래서 **원본 SVG 의 좌표와 래스터의 실제 픽셀**을 둘 다 읽어서 지킨다 —
/// 둘 중 한쪽만 고치면(예: SVG 는 바꿨는데 PNG 를 다시 안 만들면) 여기서 깨진다.
void main() {
  final svg = File('assets/icon/app_icon.svg').readAsStringSync();

  // OVERRIDES §8 의 참고 좌표·색. 이 목록이 아이콘의 정본이다.
  const background = _Rect(
    x: 0,
    y: 0,
    width: 120,
    height: 120,
    rx: 0,
    fill: '#FAFAF9',
  );
  const tiles = [
    _Rect(x: 12, y: 43, width: 30, height: 34, rx: 7, fill: '#EA580C'),
    _Rect(x: 46, y: 43, width: 30, height: 34, rx: 7, fill: '#A8A29E'),
    _Rect(x: 80, y: 43, width: 30, height: 34, rx: 7, fill: '#EA580C'),
  ];

  group('원본 SVG', () {
    test('OVERRIDES §8 의 배경 + 타일 3칸을 그 좌표 그대로 담는다', () {
      expect(svg, contains('viewBox="0 0 120 120"'));

      final rects = _rectAttributes(svg);
      expect(
        rects,
        hasLength(4),
        reason: '배경 1 + 타일 3 — 다른 도형이 끼면 아이콘이 OVERRIDES §8 이 아니다',
      );
      expect(rects.first, background.attributes);
      expect(rects.skip(1).toList(), [
        for (final tile in tiles) tile.attributes,
      ]);
    });

    test('글자가 없다 — 스토어는 앱당 아이콘 하나라 언어 중립이어야 한다', () {
      for (final element in [
        '<text',
        '<tspan',
        '<path',
        '<image',
        'font-family',
      ]) {
        expect(svg, isNot(contains(element)), reason: '$element 가 들어 있다');
      }
    });

    test('가운데 칸은 아이콘에서만 어둡고, 앱의 tile-wrong 토큰은 그대로다', () {
      // 아이콘은 글자가 없어서 칸을 면 대비로만 알린다. 보드 타일은 28pt+ 글자가
      // 대비를 만들기 때문에 같이 바꾸지 않는다 — 바꾸면 목업·골든이 다 틀어진다.
      expect(tiles[1].fill, '#A8A29E');
      expect(AppColors.light.tileWrong, const ui.Color(0xFFD6D3D1));
    });
  });

  group('1024 래스터 (iOS 1024 · Android 레거시)', () {
    test('SVG 와 같은 네 색을 그 자리에 담고, 투명한 곳이 없다', () async {
      final image = await _decode('assets/icon/app_icon.png');

      expect(image.width, 1024);
      expect(image.height, 1024);

      const scale = 1024 / 120;
      expect(image.at(10, 10), background.fill, reason: '배경');
      for (final tile in tiles) {
        final center = tile.center * scale;
        expect(image.at(center.dx.round(), center.dy.round()), tile.fill);
      }
      expect(image.alphaAt(10, 10), 255, reason: 'iOS 1024 는 알파를 못 쓴다');
    });
  });

  group('Android adaptive 전경', () {
    test('배경은 투명하고 마크는 안전 영역(안쪽 66%) 안에 있다', () async {
      final image = await _decode('assets/icon/app_icon_foreground.png');

      expect(image.alphaAt(10, 10), 0, reason: '전경은 배경색을 품지 않는다');

      final bounds = image.opaqueBounds();
      const safeMargin = 1024 * (1 - 0.72) / 2;
      expect(bounds.left, greaterThanOrEqualTo(safeMargin));
      expect(bounds.right, lessThanOrEqualTo(1024 - safeMargin));
      expect(bounds.top, greaterThanOrEqualTo(safeMargin));
      expect(bounds.bottom, lessThanOrEqualTo(1024 - safeMargin));

      // 마크는 세 칸 그대로다 — 가운데 높이에서 왼·가운데·오른쪽 칸 색을 읽는다.
      // 칸 중심의 자리는 SVG 좌표를 마크 폭에 대한 비율로 바꿔 구한다.
      final markLeft = tiles.first.x;
      final markWidth = tiles.last.x + tiles.last.width - markLeft;
      final pixelWidth = bounds.right - bounds.left;
      final middle = ((bounds.top + bounds.bottom) / 2).round();
      for (final tile in tiles) {
        final x =
            bounds.left + pixelWidth * (tile.center.dx - markLeft) / markWidth;
        expect(
          image.at(x.round(), middle),
          tile.fill,
          reason: '${tile.x} 자리 칸',
        );
      }
    });
  });

  group('30px 렌더 (스토어 목록에서 가장 작게 보이는 크기)', () {
    test('세 칸이 배경과 구분된다 — 측정한 대비비', () async {
      final image = await _decode(
        '../.scratch/store-launch/design/icon-30px.png',
      );

      expect(image.width, 30);
      expect(image.height, 30);

      const scale = 30 / 120;
      final backgroundPixel = image.at(2, 2);
      final ratios = [
        for (final tile in tiles)
          _contrastRatio(
            image.at(
              (tile.center.dx * scale).round(),
              (tile.center.dy * scale).round(),
            ),
            backgroundPixel,
          ),
      ];

      // 양끝 brand 칸은 3:1 이상(WCAG 1.4.11 의 비텍스트 기준)을 넘고,
      // 가운데 칸은 #D6D3D1 의 1.43:1 에서 #A8A29E 의 2.4:1 로 올라간다.
      // 2.4:1 을 그대로 쓰는 이유는 README "35." — 가운데 칸이 brand 보다
      // 무거워지면("한 칸이 가려졌다" 가 아니라 "가운데가 주인공") 마크가 뒤집힌다.
      expect(ratios[0], greaterThan(3));
      expect(ratios[2], greaterThan(3));
      expect(ratios[1], greaterThan(2));
      expect(
        ratios[1],
        lessThan(ratios[0]),
        reason: '가운데 칸은 brand 칸보다 가벼워야 한다',
      );
      expect(
        _contrastRatio('#D6D3D1', backgroundPixel),
        lessThan(1.5),
        reason: 'OVERRIDES §8 이 적어 둔 "구분이 안 되는" 값',
      );
    });
  });

  group('pubspec 설정', () {
    final pubspec = File('pubspec.yaml').readAsStringSync();
    final launcherIcons = _block(pubspec, 'flutter_launcher_icons');
    final splash = _block(pubspec, 'flutter_native_splash');

    test('flutter_launcher_icons 는 라이트 배경 + 분리된 adaptive 전경을 쓴다', () {
      expect(launcherIcons, contains('image_path: assets/icon/app_icon.png'));
      expect(launcherIcons, contains('adaptive_icon_background: "#FAFAF9"'));
      expect(
        launcherIcons,
        contains(
          'adaptive_icon_foreground: assets/icon/app_icon_foreground.png',
        ),
      );
      expect(launcherIcons, contains('remove_alpha_ios: true'));
    });

    test('flutter_native_splash 는 라이트·다크가 같은 배경 + 같은 마크다', () {
      for (final key in ['color', 'color_dark']) {
        expect(splash, contains('$key: "#FAFAF9"'));
      }
      for (final key in ['image', 'image_dark']) {
        expect(splash, contains('$key: assets/icon/app_icon_foreground.png'));
      }
      // Android 12+ 는 별도 블록을 봐서, 안 적으면 라이트/다크가 갈린다.
      expect(_block(splash, '  android_12'), contains('color_dark: "#FAFAF9"'));
    });

    test('Android 네이티브 자산도 같은 색으로 다시 만들어져 있다', () {
      expect(
        File('android/app/src/main/res/values/colors.xml').readAsStringSync(),
        contains('<color name="ic_launcher_background">#FAFAF9</color>'),
      );
      for (final styles in ['values-v31', 'values-night-v31']) {
        expect(
          File(
            'android/app/src/main/res/$styles/styles.xml',
          ).readAsStringSync(),
          contains(
            '<item name="android:windowSplashScreenBackground">#FAFAF9</item>',
          ),
          reason: '$styles — Android 12+ 스플래시 배경',
        );
      }
    });
  });
}

/// SVG `<rect>` 하나. 이 테스트가 OVERRIDES §8 을 적어 두는 자리다.
class _Rect {
  const _Rect({
    required this.x,
    required this.y,
    required this.width,
    required this.height,
    required this.rx,
    required this.fill,
  });

  final double x;
  final double y;
  final double width;
  final double height;
  final double rx;
  final String fill;

  ui.Offset get center => ui.Offset(x + width / 2, y + height / 2);

  Map<String, String> get attributes => {
    'x': _number(x),
    'y': _number(y),
    'width': _number(width),
    'height': _number(height),
    'rx': _number(rx),
    'fill': fill,
  };

  static String _number(double value) => value.toStringAsFixed(0);
}

final _rect = RegExp(r'<rect\s([^>]*?)/>');
final _attribute = RegExp('([a-z-]+)="([^"]*)"');

List<Map<String, String>> _rectAttributes(String svg) => [
  for (final match in _rect.allMatches(svg))
    {
      for (final attribute in _attribute.allMatches(match.group(1)!))
        attribute.group(1)!: attribute.group(2)!,
    },
];

/// `key:` 로 시작하는 블록의 본문. 같은 들여쓰기의 다음 키에서 끊는다
/// (`yaml` 패키지는 앱 의존성이 아니라 쓰지 않는다 — 읽는 건 네 줄짜리 설정이다).
String _block(String yaml, String key) {
  final lines = yaml.split('\n');
  final indent = key.length - key.trimLeft().length;
  final start = lines.indexWhere((line) => line.startsWith('$key:'));
  if (start < 0) throw ArgumentError('$key 블록이 없다');

  final body = [lines[start]];
  for (final line in lines.skip(start + 1)) {
    final trimmed = line.trimLeft();
    final startsNewKey =
        trimmed.isNotEmpty &&
        !trimmed.startsWith('#') &&
        line.length - trimmed.length <= indent;
    if (startsNewKey) break;
    body.add(line);
  }
  return body.join('\n');
}

Future<_Raster> _decode(String path) async {
  final codec = await ui.instantiateImageCodec(File(path).readAsBytesSync());
  final frame = await codec.getNextFrame();
  final data = await frame.image.toByteData();
  return _Raster(
    frame.image.width,
    frame.image.height,
    Uint8List.view(data!.buffer),
  );
}

/// 디코딩한 PNG 의 픽셀을 읽는다(RGBA, 행 우선).
class _Raster {
  _Raster(this.width, this.height, this.pixels);

  final int width;
  final int height;
  final Uint8List pixels;

  int _offset(int x, int y) => (y * width + x) * 4;

  String at(int x, int y) {
    final offset = _offset(x, y);
    return '#'
            '${pixels[offset].toRadixString(16).padLeft(2, '0')}'
            '${pixels[offset + 1].toRadixString(16).padLeft(2, '0')}'
            '${pixels[offset + 2].toRadixString(16).padLeft(2, '0')}'
        .toUpperCase();
  }

  int alphaAt(int x, int y) => pixels[_offset(x, y) + 3];

  /// 알파가 있는 픽셀을 감싸는 사각형. adaptive 전경의 안전 영역 검사에 쓴다.
  ({int left, int top, int right, int bottom}) opaqueBounds() {
    var left = width;
    var top = height;
    var right = 0;
    var bottom = 0;
    for (var y = 0; y < height; y++) {
      for (var x = 0; x < width; x++) {
        if (alphaAt(x, y) < 8) continue;
        left = math.min(left, x);
        top = math.min(top, y);
        right = math.max(right, x);
        bottom = math.max(bottom, y);
      }
    }
    return (left: left, top: top, right: right, bottom: bottom);
  }
}

/// WCAG 2.x 상대 휘도 대비비. 아이콘은 글자가 없어서 "칸이 보이는가" 를
/// 눈대중 대신 이 숫자로 적는다(README "35." 가 같은 값을 인용한다).
double _contrastRatio(String a, String b) {
  final first = _relativeLuminance(a);
  final second = _relativeLuminance(b);
  final lighter = math.max(first, second);
  final darker = math.min(first, second);
  return (lighter + 0.05) / (darker + 0.05);
}

double _relativeLuminance(String hex) {
  final value = int.parse(hex.substring(1), radix: 16);
  final channels =
      [
            for (final shift in [16, 8, 0]) ((value >> shift) & 0xFF) / 255,
          ]
          .map(
            (channel) => channel <= 0.03928
                ? channel / 12.92
                : math.pow((channel + 0.055) / 1.055, 2.4) as double,
          )
          .toList();
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}
