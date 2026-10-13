import base64
import hashlib

from cryptography.fernet import Fernet
from flask import current_app

# 파생 키의 용도 구분자. 나중에 다른 값을 암호화하게 되면 용도별로 다른 키를 쓴다.
_KEY_PURPOSE = b"account-provider-refresh-token"


def _fernet() -> Fernet:
    """SECRET_KEY 에서 Fernet 키를 파생한다.

    암호화 키를 설정값으로 따로 두지 않은 이유: 보관하는 비밀이 애플 refresh
    token 하나뿐이고, 그 값의 수명은 SECRET_KEY 와 어차피 같다(SECRET_KEY 가
    바뀌면 세션 쿠키·CSRF 토큰도 전부 무효가 되는 서비스다). 설정값을 하나 더
    늘려 "둘 중 뭘 잃어버렸나"를 운영에서 구분하게 만들 이유가 없다.

    Fernet 키는 32바이트 urlsafe base64 라서 SHA-256 결과를 그대로 쓸 수 있다.
    """
    secret = current_app.config["SECRET_KEY"]
    digest = hashlib.sha256(_KEY_PURPOSE + b":" + secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """암호문을 복호화한다. 키가 다르거나 값이 깨졌으면 `InvalidToken` 이 올라간다."""
    return _fernet().decrypt(ciphertext.encode()).decode()
