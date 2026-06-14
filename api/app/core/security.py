from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_fernet = Fernet(settings.ENCRYPTION_KEY.encode())

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire, "type": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "refresh"},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def encrypt_value(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode()).decode()
