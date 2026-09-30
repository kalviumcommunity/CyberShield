from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, Optional, Union
import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User

logger = logging.getLogger("cybershield.auth_service")


def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt with a randomized salt.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a stored bcrypt hash.
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.warning("Password verification exception: %s", e)
        return False


def create_access_token(
    subject: Union[User, Dict[str, Any], str, int],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Creates and signs a JWT access token with user claims and expiration timestamp.
    Supports passing a User model instance, a claim dictionary, or a user ID.
    """
    if isinstance(subject, User):
        to_encode = {
            "sub": str(subject.id),
            "email": subject.email,
            "role": subject.role,
            "name": subject.name,
        }
    elif isinstance(subject, dict):
        to_encode = subject.copy()
    else:
        to_encode = {"sub": str(subject)}

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and validates a signed JWT token.
    Returns decoded payload dictionary, or None if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception) as e:
        logger.debug("JWT decode failure: %s", e)
        return None


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> Optional[User]:
    """
    Authenticates a user by email and plaintext password.
    Returns the User record if valid, otherwise None.
    """
    if not email or not password:
        return None
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_user(
    db: Session,
    name: str,
    email: str,
    password: str,
    role: str = "analyst",
) -> User:
    """
    Creates and stores a new user in PostgreSQL with bcrypt hashed password.
    """
    clean_email = email.strip().lower()
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise ValueError(f"User with email '{clean_email}' already exists.")

    assigned_role = role if role in ["admin", "analyst"] else "analyst"
    hashed_pwd = hash_password(password)

    new_user = User(
        name=name.strip(),
        email=clean_email,
        password_hash=hashed_pwd,
        role=assigned_role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def init_default_users(db: Session) -> None:
    """
    Ensures default admin and analyst users exist in PostgreSQL for testing and initial platform access.
    """
    default_users = [
        {
            "name": "System Administrator",
            "email": "admin@cybershield.io",
            "password": "AdminPass123!",
            "role": "admin",
        },
        {
            "name": "Security Analyst",
            "email": "analyst@cybershield.io",
            "password": "AnalystPass123!",
            "role": "analyst",
        },
    ]

    for u in default_users:
        existing = db.query(User).filter(User.email == u["email"]).first()
        if not existing:
            try:
                create_user(
                    db=db,
                    name=u["name"],
                    email=u["email"],
                    password=u["password"],
                    role=u["role"],
                )
                logger.info("Initialized default %s user: %s", u["role"], u["email"])
            except Exception as e:
                logger.warning("Could not create default user %s: %s", u["email"], e)
