from app.security.auth import create_access_token, verify_access_token
from app.security.password import hash_password, verify_password
from app.security.sanitize import sanitize_cpf, sanitize_text
import uuid


def test_password_hash():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_access_token():
    uid = uuid.uuid4()
    token = create_access_token("user@test.com", "admin", uid)
    payload = verify_access_token(token)
    assert payload is not None
    assert payload["user_id"] == str(uid)
    assert payload["user_type"] == "admin"


def test_sanitize_text():
    assert sanitize_text("  hello  ") == "hello"
    assert len(sanitize_text("x" * 3000, max_length=100)) == 100


def test_sanitize_cpf():
    assert sanitize_cpf("123.456.789-00") == "12345678900"
