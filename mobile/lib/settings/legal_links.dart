import 'package:chosung/config/app_env.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

/// S4 설정이 웹으로 보내는 문서. 경로는 `app/web.py` 의 라우트와 같다.
enum LegalDocument {
  privacy('privacy'),
  terms('terms')
  ;

  const LegalDocument(this.path);

  final String path;
}

/// 법적 문서 URL. 웹과 API 가 같은 Flask 앱이라 따로 주입받지 않고
/// `API_BASE_URL` 에서 `/api/v1` 을 떼어 만든다 — 빌드 설정을 하나 더 두면
/// 둘이 다른 환경을 가리키는 조합(개발 API + 운영 문서)이 생긴다.
///
/// [uiLanguage] 는 `?lang=` 으로 넘긴다. 서버도 같은 규칙으로 ko/en 본문을
/// 고르므로(`resolve_ui_language`) 앱 언어와 문서 언어가 어긋나지 않는다.
String legalDocumentUrl({
  required LegalDocument document,
  required String uiLanguage,
  String apiBaseUrl = AppEnv.apiBaseUrl,
}) {
  var origin = apiBaseUrl;
  while (origin.endsWith('/')) {
    origin = origin.substring(0, origin.length - 1);
  }
  const apiPrefix = '/api/v1';
  if (origin.endsWith(apiPrefix)) {
    origin = origin.substring(0, origin.length - apiPrefix.length);
  }
  return '$origin/${document.path}?lang=$uiLanguage';
}

/// 법적 문서를 외부 브라우저로 연다. 테스트는 이 provider 를 가짜로 덮어
/// URL 만 확인한다(S7 의 `storeLauncherProvider` 와 같은 모양).
final webLinkLauncherProvider = Provider<Future<void> Function(String url)>(
  (ref) =>
      (url) async =>
          launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication),
);
