"""CSRF protection."""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

settings = get_settings()
_serializer = URLSafeTimedSerializer(settings.csrf_secret_key)


def generate_csrf_token(session_id: str) -> str:
    return _serializer.dumps({"session": session_id})


def validate_csrf_token(token: str, session_id: str, max_age: int = 3600) -> bool:
    try:
        data = _serializer.loads(token, max_age=max_age)
        return data.get("session") == session_id
    except (BadSignature, SignatureExpired):
        return False


class CSRFProtection:
    """Middleware helper for form CSRF validation."""

    @staticmethod
    def token_for_session(session_id: str) -> str:
        return generate_csrf_token(session_id)

    @staticmethod
    def validate(token: str, session_id: str) -> bool:
        return validate_csrf_token(token, session_id)
