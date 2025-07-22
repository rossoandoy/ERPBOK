"""
Authentication utilities for ERPFTS Phase1 MVP

Provides password hashing, JWT token creation/validation,
and user authentication helper functions.
"""

from datetime import datetime, timedelta
from typing import Optional, Union
from passlib.context import CryptContext
from jose import JWTError, jwt

from ..core.config import settings
from ..core.exceptions import AuthenticationError

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Token expiration time (defaults to ACCESS_TOKEN_EXPIRE_MINUTES)
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Dictionary of token claims
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise AuthenticationError(
            message="Could not validate credentials",
            error_code="INVALID_TOKEN",
            details={"jwt_error": str(e)}
        )


def get_token_user_id(token: str) -> Optional[str]:
    """
    Extract user ID from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        User ID if valid, None if invalid
    """
    try:
        payload = decode_access_token(token)
        return payload.get("sub")
    except AuthenticationError:
        return None


def create_user_token(user_id: str, username: str, is_admin: bool = False) -> str:
    """
    Create an access token for a specific user.
    
    Args:
        user_id: User's unique identifier
        username: User's username
        is_admin: Whether user has admin privileges
        
    Returns:
        JWT token string
    """
    token_data = {
        "sub": user_id,
        "username": username,
        "is_admin": is_admin,
        "type": "access_token",
    }
    
    return create_access_token(data=token_data)


def validate_token_claims(token: str, required_claims: list = None) -> dict:
    """
    Validate token and check for required claims.
    
    Args:
        token: JWT token string
        required_claims: List of required claim keys
        
    Returns:
        Token payload dictionary
        
    Raises:
        AuthenticationError: If token is invalid or missing required claims
    """
    payload = decode_access_token(token)
    
    if required_claims:
        missing_claims = []
        for claim in required_claims:
            if claim not in payload:
                missing_claims.append(claim)
        
        if missing_claims:
            raise AuthenticationError(
                message="Token missing required claims",
                error_code="MISSING_CLAIMS",
                details={"missing_claims": missing_claims}
            )
    
    return payload