import 'package:easy_localization/easy_localization.dart';

/// UI 언어는 기기 설정을 따른다 — 그래서 **`startLocale` 없이** 앱을 띄운다.
/// easy_localization 은 기기 언어를 컨트롤러의 `late static` 필드에 담아두고
/// 이 초기화에서만 채우기 때문에, 호출하지 않으면 첫 빌드에서
/// `LateInitializationError` 로 앱이 죽는다. `saveLocale: false` 는 저장만
/// 끄는 옵션이라 이 초기화를 대신하지 않는다.
Future<void> initializeLocalization() => EasyLocalization.ensureInitialized();
