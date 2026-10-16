import enum


class WordCategory(enum.StrEnum):
    GENERAL = "general"
    BOOK_TITLE = "book_title"


class OAuthProvider(enum.StrEnum):
    GOOGLE = "google"
    APPLE = "apple"


class PuzzleLanguage(enum.StrEnum):
    """퍼즐 언어 — 플레이어가 고르는 문제의 언어. UI 언어와 별개다(CONTEXT.md)."""

    KO = "ko"
    EN = "en"


class SubscriptionStore(enum.StrEnum):
    """구독을 판 스토어. 영수증 모양과 검증 경로가 여기서 갈린다."""

    APPLE = "apple"
    GOOGLE = "google"


class SubscriptionEnvironment(enum.StrEnum):
    """스토어의 구매 환경. App Review 가 프로덕션 서버에 Sandbox 영수증을 보내므로
    (US 34a) 행에 남겨두고, 재조회 때 같은 환경으로 다시 물어본다. 값 표기는
    Apple 의 `environment` 그대로다 — Google 은 `testPurchase` 유무로 정한다.
    """

    SANDBOX = "Sandbox"
    PRODUCTION = "Production"


class SubscriptionStatus(enum.StrEnum):
    """스토어마다 다른 상태 이름을 하나로 정규화한 것(스펙 §A.8, ADR 0003).

    권한(광고를 끄느냐)은 이 상태를 보고 별도 순수 함수가 판정한다 — 스토어
    용어를 서비스 전체에 퍼뜨리지 않으려고 한 번 접어두는 자리다.
    """

    ACTIVE = "active"
    GRACE = "grace"
    HOLD = "hold"
    EXPIRED = "expired"
    REVOKED = "revoked"
    # 구매 교체(Google linkedPurchaseToken)로 다른 행이 이어받은 옛 구독.
    REPLACED = "replaced"


class CandidateStatus(enum.StrEnum):
    """LLM 이 만든 단어 후보의 처리 상태(LLM 출제 파이프라인).

    `proposed` 는 규칙을 통과해 운영자 승인을 기다리는 행, `approved` 는 승인해서
    `word` 로 들어간 행, `rejected` 는 규칙에 걸렸거나(`reject_reason` 에 사유)
    운영자가 거절한 행이다. 탈락 행도 지우지 않고 남긴다 — 규칙 통과율이 곧
    프롬프트 품질 지표라서(README "설계 판단").
    """

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class LlmCallResult(enum.StrEnum):
    """LLM 호출 한 건의 결과. `retried` 는 재시도 끝에 성공한 호출의 중간 실패다."""

    SUCCESS = "success"
    FAILURE = "failure"
    RETRIED = "retried"
