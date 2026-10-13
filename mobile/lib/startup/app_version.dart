import 'package:package_info_plus/package_info_plus.dart';

/// `/api/v1/config` 의 `min_app_version` 과 설치된 앱 버전을 비교한다.
///
/// 어느 쪽이든 읽을 수 없는 문자열이면 `false` — 강제 업데이트 화면은 앱으로
/// 들어가는 길을 완전히 막기 때문에, 판정에 실패했을 때는 통과시키는 쪽으로
/// 기울인다. 점검 모드와 달리 여기서 틀리면 사용자가 할 수 있는 일이 없다.
bool isUpdateRequired({required String current, required String minimum}) {
  final currentParts = _parseVersion(current);
  final minimumParts = _parseVersion(minimum);
  if (currentParts == null || minimumParts == null) return false;

  final length = currentParts.length > minimumParts.length
      ? currentParts.length
      : minimumParts.length;
  for (var i = 0; i < length; i++) {
    final a = i < currentParts.length ? currentParts[i] : 0;
    final b = i < minimumParts.length ? minimumParts[i] : 0;
    if (a != b) return a < b;
  }
  return false;
}

/// `1.2.3+45` → `[1, 2, 3]`. 빌드 번호는 스토어 심사용 카운터라 비교하지 않는다.
List<int>? _parseVersion(String raw) {
  final withoutBuild = raw.split('+').first.trim();
  if (withoutBuild.isEmpty) return null;

  final parts = <int>[];
  for (final part in withoutBuild.split('.')) {
    final number = int.tryParse(part);
    if (number == null || number < 0) return null;
    parts.add(number);
  }
  return parts;
}

/// 설치된 앱의 버전 문자열(`pubspec.yaml` 의 `version` 앞부분).
Future<String> installedAppVersion() async {
  final info = await PackageInfo.fromPlatform();
  return info.version;
}
