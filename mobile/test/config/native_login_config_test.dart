import 'dart:io';

import 'package:chosung/config/app_env.dart';
import 'package:flutter_test/flutter_test.dart';

/// 네이티브 로그인 설정은 Dart 쪽 analyze/test 가 전혀 건드리지 않는다.
/// `ios_project_test.dart` 와 같은 이유로 설정 파일을 직접 읽어서 지킨다 —
/// 여기가 비면 앱은 뜨지만 계정 연결만 조용히 실패한다.
void main() {
  final infoPlist = File('ios/Runner/Info.plist').readAsStringSync();

  group('iOS 구글 로그인(스펙 §A.6 표)', () {
    test('Info.plist 가 GIDClientID 와 역방향 URL 스킴을 빌드 설정에서 받는다', () {
      // 값을 파일에 박지 않는다 — 콘솔 등록 전이라 가짜 ID 를 커밋하면
      // "설정은 됐는데 틀린" 빌드가 스토어로 간다.
      expect(infoPlist, contains('<key>GIDClientID</key>'));
      expect(infoPlist, contains(r'<string>$(GOOGLE_IOS_CLIENT_ID)</string>'));
      expect(infoPlist, contains('<key>CFBundleURLSchemes</key>'));
      expect(
        infoPlist,
        contains(r'<string>$(GOOGLE_IOS_URL_SCHEME)</string>'),
      );
    });

    test('Debug·Release xcconfig 가 Secrets.xcconfig 를 선택적으로 읽는다', () {
      for (final name in const ['Debug', 'Release']) {
        final config = File('ios/Flutter/$name.xcconfig').readAsStringSync();
        // `#include?` 라서 파일이 없어도 빌드가 깨지지 않는다.
        expect(
          config,
          contains('#include? "Secrets.xcconfig"'),
          reason: '$name.xcconfig',
        );
      }

      final example = File(
        'ios/Flutter/Secrets.xcconfig.example',
      ).readAsStringSync();
      expect(example, contains('GOOGLE_IOS_CLIENT_ID'));
      expect(example, contains('GOOGLE_IOS_URL_SCHEME'));
      // 실제 값은 커밋되지 않는다(.gitignore).
      expect(File('ios/Flutter/Secrets.xcconfig').existsSync(), isFalse);
      expect(
        File('.gitignore').readAsStringSync(),
        contains('/ios/Flutter/Secrets.xcconfig'),
      );
    });
  });

  test('Sign in with Apple 권한이 Runner 타깃 세 설정에 다 걸려 있다', () {
    final entitlements = File(
      'ios/Runner/Runner.entitlements',
    ).readAsStringSync();
    expect(
      entitlements,
      contains('<key>com.apple.developer.applesignin</key>'),
    );
    expect(entitlements, contains('<string>Default</string>'));

    // Debug/Release/Profile 셋 다 걸려 있어야 한다 — 하나만 빠져도 그 빌드에서
    // sign_in_with_apple 이 1000 오류로 떨어진다.
    final pbxproj = File(
      'ios/Runner.xcodeproj/project.pbxproj',
    ).readAsStringSync();
    expect(
      'CODE_SIGN_ENTITLEMENTS = Runner/Runner.entitlements;'
          .allMatches(pbxproj)
          .length,
      3,
    );
  });

  test('Android serverClientId 는 dart-define 으로 들어온다', () {
    // 테스트에서는 안 넘기므로 비어 있고, 그때는 null 로 떨어뜨린다 —
    // 플러그인에 빈 문자열을 주면 오류 메시지가 엉뚱해진다.
    expect(AppEnv.googleServerClientId, isEmpty);
    expect(AppEnv.googleServerClientIdOrNull, isNull);

    // 릴리스 빌드는 워크플로와 fastlane 둘 다에서 이 값을 반드시 넘긴다.
    final workflow = File(
      '../.github/workflows/flutter.yml',
    ).readAsStringSync();
    expect(
      '--dart-define=GOOGLE_SERVER_CLIENT_ID='.allMatches(workflow).length,
      2,
      reason: 'Android·iOS 빌드 잡 둘 다',
    );
    for (final platform in const ['android', 'ios']) {
      expect(
        File('$platform/fastlane/Fastfile').readAsStringSync(),
        contains('GOOGLE_SERVER_CLIENT_ID'),
        reason: platform,
      );
    }
  });
}
