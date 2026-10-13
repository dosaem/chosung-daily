# 앱 로그인은 네이티브 SDK 의 id_token 을 서버에 교환하는 방식으로 한다

웹은 브라우저 세션 쿠키 + OAuth 리다이렉트로 계정을 연결하지만, 앱은 같은 흐름을 WebView 에 태우지 않는다. 구글이 임베디드 WebView OAuth 를 차단하고, 시스템 브라우저로 열면 세션 쿠키 기반 CSRF 방어가 깨져서 PKCE 식 상태 저장이 추가로 필요해진다. 대신 앱이 `google_sign_in` / `sign_in_with_apple` 로 받은 id_token 을 게스트 Bearer 토큰과 함께 서버에 보내고, 서버가 JWKS 로 서명·aud 를 검증한 뒤 같은 Account 테이블에 연결한다. 연결 요청 자체가 Bearer 로 인증되므로 로그인 CSRF 가 구조적으로 없다. 비용은 GCP 에 iOS/Android OAuth 클라이언트 2개를 더 만드는 것(사람 작업).

**애플 토큰 보관**: 애플 계정 삭제 시 Apple revoke 에는 id_token 이 아니라 refresh/access token 이 필요하므로, 앱은 `authorization_code` 도 함께 보내고 서버가 교환한 refresh token 을 암호화해 Account 에 보관한다. 웹 콜백도 같은 컬럼에 저장한다.

**Consequences**: 구글 id_token 의 `aud` 는 iOS 에선 iOS 클라이언트 ID, Android 에선 `serverClientId` 로 준 **웹 클라이언트 ID** 다(Android 클라이언트 ID 는 SHA-1 검증용). 애플은 iOS 에서만 지원한다 — Android 는 웹 플로우와 서버 콜백 라우트가 추가로 필요해 범위 밖. 웹과 앱의 로그인 진입 경로가 둘이지만 Account 모델과 연결/전환 규칙은 하나다. 서버는 구글·애플 JWKS 를 캐시해야 한다.
