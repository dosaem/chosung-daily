import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';

enum FirebaseBootstrap { initialized, skipped }

/// Firebase 설정 파일(`google-services.json` / `GoogleService-Info.plist`)은
/// 비밀이라 커밋하지 않는다(`.example` 자리표시자만 둔다). 파일이 없으면
/// `Firebase.initializeApp` 이 던지는데, **그걸로 앱이 죽으면 CI 와 새로
/// 클론한 로컬에서 디버그 실행조차 못 한다** — 그래서 건너뛴다.
///
/// 분석(Analytics)은 티켓 26 가 이 결과를 보고 켠다.
Future<FirebaseBootstrap> initializeFirebase({
  Future<void> Function()? initialize,
}) async {
  try {
    await (initialize ?? Firebase.initializeApp)();
    return FirebaseBootstrap.initialized;
  } on Exception catch (error) {
    debugPrint('Firebase 초기화를 건너뜁니다: $error');
    return FirebaseBootstrap.skipped;
  }
}
