# 스토어 응답 fixture

구독 검증(티켓 12)의 상태 매핑 순수 함수와 서비스 테스트가 읽는, 실제 스토어
응답 모양 그대로의 JSON 이다. 네트워크를 타지 않고 상태 전이를 고정하려고 둔다.

- `apple_*.json` — App Store Server API `GET /inApps/v1/subscriptions/{id}` 의
  `data[].lastTransactions[]` 항목(`LastTransactionsItem`) 하나. 실제 응답에서는
  `signedTransactionInfo`·`signedRenewalInfo` 가 JWS 문자열이라 여기서는
  **검증 후 디코딩된 페이로드**(`JWSTransactionDecodedPayload` /
  `JWSRenewalInfoDecodedPayload`)를 그 자리에 넣었다. 날짜는 Apple 그대로
  epoch milliseconds.
- `play_*.json` — Play Developer API `purchases.subscriptionsv2.get` 의
  `SubscriptionPurchaseV2` 응답. 날짜는 Google 그대로 RFC 3339.

`expiresDate`/`expiryTime` 은 테스트가 "지금"을 기준으로 판단하지 않도록 고정
시각(2026-11-01T00:00:00Z)을 쓴다 — 권한 판정(만료 비교)은 티켓 13 이고,
여기서 검증하는 건 "스토어 상태 → 우리 status" 매핑뿐이다.
