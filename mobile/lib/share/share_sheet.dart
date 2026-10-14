import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart';

/// 네이티브 공유 시트를 띄운다(US 10). 테스트는 이 provider 를 덮어 **무슨
/// 텍스트가 나갔는지**만 본다 — 플랫폼 시트 자체는 OS 것이라 볼 게 없다.
typedef ShareText = Future<void> Function(String text);

/// `share_plus` 래퍼. 결과(`ShareResult.status`)는 쓰지 않는다 — Android·macOS
/// 는 사용자가 무엇을 골랐는지 알려주지 않아서, "공유 시트를 띄웠다" 까지가
/// 세 플랫폼에서 같은 뜻을 갖는 유일한 지점이다.
Future<void> shareWithSystemSheet(String text) async {
  await SharePlus.instance.share(ShareParams(text: text));
}

final shareTextProvider = Provider<ShareText>((ref) => shareWithSystemSheet);
