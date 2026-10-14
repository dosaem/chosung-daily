import 'package:chosung/settings/legal_links.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('legalDocumentUrl', () {
    test('API base 에서 /api/v1 을 떼고 UI 언어를 붙인다', () {
      expect(
        legalDocumentUrl(
          document: LegalDocument.privacy,
          uiLanguage: 'ko',
          apiBaseUrl: 'https://chosung.dosaem.com/api/v1',
        ),
        'https://chosung.dosaem.com/privacy?lang=ko',
      );
      expect(
        legalDocumentUrl(
          document: LegalDocument.terms,
          uiLanguage: 'en',
          apiBaseUrl: 'https://chosung.dosaem.com/api/v1',
        ),
        'https://chosung.dosaem.com/terms?lang=en',
      );
    });

    test('끝 슬래시와 포트가 있어도 같은 호스트를 가리킨다', () {
      expect(
        legalDocumentUrl(
          document: LegalDocument.privacy,
          uiLanguage: 'ko',
          apiBaseUrl: 'http://10.0.2.2:8089/api/v1/',
        ),
        'http://10.0.2.2:8089/privacy?lang=ko',
      );
    });

    test('하위 경로에 올린 API 라도 그 앞까지만 남긴다', () {
      expect(
        legalDocumentUrl(
          document: LegalDocument.terms,
          uiLanguage: 'ko',
          apiBaseUrl: 'https://example.test/chosung/api/v1',
        ),
        'https://example.test/chosung/terms?lang=ko',
      );
    });
  });
}
