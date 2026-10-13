"""애플 refresh token 보관용 암복호. 키는 SECRET_KEY 에서 파생한다."""

import pytest
from cryptography.fernet import InvalidToken

from app.utils.crypto import decrypt_secret, encrypt_secret


def test_roundtrip(app):
    encrypted = encrypt_secret("apple-refresh-token")

    assert encrypted != "apple-refresh-token"
    assert decrypt_secret(encrypted) == "apple-refresh-token"


def test_same_plaintext_encrypts_to_different_ciphertext(app):
    # Fernet 은 매번 새 IV 를 쓴다 — 같은 토큰을 두 계정이 쓰는지 암호문만 보고
    # 알 수 없어야 한다.
    assert encrypt_secret("same") != encrypt_secret("same")


def test_other_secret_key_cannot_decrypt(app):
    encrypted = encrypt_secret("apple-refresh-token")

    app.config["SECRET_KEY"] = "완전히-다른-키"

    with pytest.raises(InvalidToken):
        decrypt_secret(encrypted)
