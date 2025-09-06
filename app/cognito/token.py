from datetime import datetime, timedelta

from jose import JWTError, jwt

from config import SECRET_KEY

# Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token, expected_purpose: str | None = None) -> tuple[bool, str | None]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        purpose: str = payload.get("purpose")

        if email is None:
            raise JWTError

        if expected_purpose and purpose != expected_purpose:
            raise JWTError

        return True, email
    except JWTError:
        return False, None
