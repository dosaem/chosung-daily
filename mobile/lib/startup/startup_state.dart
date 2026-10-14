import 'package:chosung/api/api_models.dart';
import 'package:flutter/foundation.dart';

/// 스플래시가 끝난 뒤 앱이 들어갈 자리. 로딩·에러는 `AsyncValue` 가 들고 있다.
@immutable
sealed class StartupState {
  const StartupState();
}

/// S7 점검 화면. `message` 는 운영자가 넣은 안내(없을 수 있다).
class StartupMaintenance extends StartupState {
  const StartupMaintenance(this.message);

  final String? message;
}

/// S7 강제 업데이트 화면. `storeUrl` 은 스토어 등록 전에는 null 이다.
class StartupUpdateRequired extends StartupState {
  const StartupUpdateRequired(this.storeUrl);

  final String? storeUrl;
}

/// 3탭 홈. 시작할 때 읽은 내 기록을 같이 들고 간다.
class StartupReady extends StartupState {
  const StartupReady(this.stats);

  final MyStats stats;
}
