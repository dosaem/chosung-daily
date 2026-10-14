import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// iOS 네이티브 설정은 Dart 쪽 analyze/test 와 Android 빌드가 전혀 건드리지
/// 않는다. 그래서 설정 파일을 직접 읽어서 지킨다 — 둘 다 리뷰에서 실제로
/// 깨진 채 넘어온 항목이다(D-22-2 최소 버전, D-22-3 한국어 앱 이름).
void main() {
  final pbxproj = File('ios/Runner.xcodeproj/project.pbxproj');

  group('iOS 최소 버전', () {
    test('프로젝트·Podfile·앱 프레임워크가 한 값이고 pod 요구치를 만족한다', () {
      final projectTargets = RegExp(
        r'IPHONEOS_DEPLOYMENT_TARGET = ([\d.]+);',
      ).allMatches(pbxproj.readAsStringSync()).map((m) => m.group(1)!).toList();
      expect(projectTargets, hasLength(3), reason: 'Debug/Release/Profile');

      // 주석(`# platform :ios, ...`)은 선언이 아니다 — 실제로 켜져 있어야 한다.
      final podfilePlatform = RegExp(
        r"^platform :ios, '([\d.]+)'",
        multiLine: true,
      ).firstMatch(File('ios/Podfile').readAsStringSync())?.group(1);
      final frameworkMinimum =
          RegExp(
                r'<key>MinimumOSVersion</key>\s*<string>([\d.]+)</string>',
              )
              .firstMatch(
                File('ios/Flutter/AppFrameworkInfo.plist').readAsStringSync(),
              )
              ?.group(1);

      expect({
        ...projectTargets,
        podfilePlatform,
        frameworkMinimum,
      }, hasLength(1));

      final declared = projectTargets.first;
      for (final requirement in _podIosRequirements().entries) {
        expect(
          _compareVersions(declared, requirement.value) >= 0,
          isTrue,
          reason:
              '${requirement.key} 는 iOS ${requirement.value} 이상을 요구한다 '
              '(현재 $declared) — CocoaPods 가 의존성을 풀지 못한다',
        );
      }
    });
  });

  group('한국어 앱 이름', () {
    test('ko.lproj/InfoPlist.strings 가 Runner 타깃 Resources 에 들어 있다', () {
      final text = pbxproj.readAsStringSync();

      final fileRef = _objectIds(
        text,
        isa: 'PBXFileReference',
        contains: ['ko.lproj/InfoPlist.strings'],
      );
      expect(fileRef, hasLength(1), reason: '한국어 InfoPlist.strings 파일 참조');

      final variantGroup = _objectIds(
        text,
        isa: 'PBXVariantGroup',
        contains: [fileRef.single],
      );
      expect(
        variantGroup,
        hasLength(1),
        reason: 'InfoPlist.strings variant group',
      );

      final buildFile = _objectIds(
        text,
        isa: 'PBXBuildFile',
        contains: ['fileRef = ${variantGroup.single}'],
      );
      expect(buildFile, hasLength(1), reason: 'Resources 에 넣을 build file');

      final resourcePhases = _objectIds(
        text,
        isa: 'PBXResourcesBuildPhase',
        contains: [buildFile.single],
      );
      expect(resourcePhases, hasLength(1), reason: 'Runner 의 Resources 단계');

      // 번들에 ko 가 들어가도 프로젝트가 ko 를 모르면 Xcode 가 리소스를
      // 지역화로 취급하지 않는다.
      expect(
        RegExp(r'knownRegions = \(([^)]*)\)').firstMatch(text)!.group(1),
        contains('ko'),
      );
    });
  });
}

/// `.dart_tool/package_config.json` 에 풀린 패키지들의 podspec 에서 iOS 최소
/// 버전 선언을 읽는다(`s.ios.deployment_target` / `s.platform = :ios, '…'`).
Map<String, String> _podIosRequirements() {
  final config =
      jsonDecode(
            File('.dart_tool/package_config.json').readAsStringSync(),
          )
          as Map<String, dynamic>;

  final requirements = <String, String>{};
  for (final package in config['packages'] as List<dynamic>) {
    final entry = package as Map<String, dynamic>;
    final root = Uri.parse(entry['rootUri'] as String);
    if (!root.isScheme('file')) continue;

    for (final dir in const ['ios', 'darwin']) {
      final directory = Directory.fromUri(root.resolve('$dir/'));
      if (!directory.existsSync()) continue;

      for (final podspec in directory.listSync().whereType<File>()) {
        if (!podspec.path.endsWith('.podspec')) continue;
        final source = podspec.readAsStringSync();
        final version =
            RegExp(
              r"s\.ios\.deployment_target\s*=\s*'([\d.]+)'",
            ).firstMatch(source)?.group(1) ??
            RegExp(
              r"s\.platform\s*=\s*:ios,\s*'([\d.]+)'",
            ).firstMatch(source)?.group(1);
        if (version == null) continue;

        final name = entry['name'] as String;
        final known = requirements[name];
        if (known == null || _compareVersions(version, known) > 0) {
          requirements[name] = version;
        }
      }
    }
  }
  return requirements;
}

int _compareVersions(String a, String b) {
  final left = a.split('.').map(int.parse).toList();
  final right = b.split('.').map(int.parse).toList();
  for (
    var i = 0;
    i < (left.length > right.length ? left.length : right.length);
    i++
  ) {
    final diff =
        (i < left.length ? left[i] : 0) - (i < right.length ? right[i] : 0);
    if (diff != 0) return diff;
  }
  return 0;
}

/// pbxproj 는 `<24자리 ID> /* 주석 */ = { isa = …; … };` 블록이 이어진 기계
/// 생성 텍스트다. 여기서는 "어떤 ID 를 품은 블록이 있나" 만 보면 되므로
/// 블록 단위로 잘라서 확인한다.
List<String> _objectIds(
  String pbxproj, {
  required String isa,
  required List<String> contains,
}) {
  final ids = <String>[];
  for (final match in RegExp(
    r'([0-9A-F]{24}) (?:/\*[^*]*\*/ )?= \{(.*?)\n?\t*\};',
    dotAll: true,
  ).allMatches(pbxproj)) {
    final body = match.group(2)!;
    if (!body.contains('isa = $isa;')) continue;
    if (contains.every(body.contains)) ids.add(match.group(1)!);
  }
  return ids;
}
