"""Authentication service — Phase 9.

Provides:
- JWT token creation/verification
- Password hashing (bcrypt)
- OAuth 2.0 token exchange (Google, GitHub, Microsoft)
- Email verification & password reset tokens
- API key generation & validation
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================


class AuthConfig(BaseModel):
    """Authentication configuration."""

    secret_key: str = "change-me-in-production-use-a-real-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    verification_token_expire_hours: int = 48
    reset_token_expire_hours: int = 2
    api_key_prefix: str = "rsvg_"
    bcrypt_rounds: int = 12

    # OAuth client IDs (set via environment)
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    oauth_redirect_base: str = "http://localhost:3000/auth/callback"


_config = AuthConfig()


def get_auth_config() -> AuthConfig:
    return _config


# =============================================================================
# Password Hashing
# =============================================================================


class PasswordHasher:
    """Secure password hashing using bcrypt."""

    def __init__(self, rounds: int = 12):
        self.rounds = rounds
        self._bcrypt = None

    def _get_bcrypt(self):
        if self._bcrypt is None:
            try:
                import bcrypt

                self._bcrypt = bcrypt
            except ImportError:
                logger.warning(
                    "bcrypt not installed, using hashlib fallback (NOT secure for production)"
                )
                self._bcrypt = None
        return self._bcrypt

    def hash_password(self, password: str) -> str:
        """Hash a plain-text password."""
        bcrypt = self._get_bcrypt()
        if bcrypt:
            salt = bcrypt.gensalt(rounds=self.rounds)
            return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        else:
            # Fallback (development only)
            return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        bcrypt = self._get_bcrypt()
        if bcrypt:
            try:
                return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
            except Exception:
                return False
        else:
            return hashlib.sha256(password.encode("utf-8")).hexdigest() == hashed


password_hasher = PasswordHasher()


# =============================================================================
# JWT Token Management
# =============================================================================


class TokenManager:
    """JWT token creation and verification."""

    def __init__(self, config: AuthConfig):
        self.config = config
        self._jwt = None

    def _get_jwt(self):
        if self._jwt is None:
            try:
                import jwt

                self._jwt = jwt
            except ImportError:
                try:
                    import jose.jwt as jose_jwt

                    self._jwt = jose_jwt
                except ImportError:
                    raise ImportError("Install PyJWT or python-jose: pip install PyJWT")
        return self._jwt

    def create_access_token(
        self,
        user_id: str,
        email: str,
        role: str = "user",
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a JWT access token."""
        jwt = self._get_jwt()

        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self.config.access_token_expire_minutes),
        }
        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create a JWT refresh token."""
        jwt = self._get_jwt()

        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.config.refresh_token_expire_days),
            "jti": secrets.token_urlsafe(16),
        }

        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def verify_token(self, token: str, expected_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        jwt = self._get_jwt()

        try:
            payload = jwt.decode(token, self.config.secret_key, algorithms=[self.config.algorithm])
            if payload.get("type") != expected_type:
                return None
            return payload
        except Exception as e:
            logger.debug(f"Token verification failed: {e}")
            return None


token_manager = TokenManager(_config)


# =============================================================================
# API Key Management
# =============================================================================


class APIKeyManager:
    """Generate and validate API keys."""

    def __init__(self, prefix: str = "rsvg_"):
        self.prefix = prefix

    def generate_key(self) -> tuple[str, str, str]:
        """
        Generate a new API key.

        Returns: (full_key, key_prefix, key_hash)
        """
        random_part = secrets.token_urlsafe(32)
        full_key = f"{self.prefix}{random_part}"
        key_prefix = full_key[:8]
        key_hash = hashlib.sha256(full_key.encode("utf-8")).hexdigest()

        return full_key, key_prefix, key_hash

    def hash_key(self, key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def get_prefix(self, key: str) -> str:
        """Get the prefix of an API key for identification."""
        return key[:8]


api_key_manager = APIKeyManager()


# =============================================================================
# Verification & Reset Tokens
# =============================================================================


def generate_verification_token() -> str:
    """Generate an email verification token."""
    return secrets.token_urlsafe(32)


def generate_reset_token() -> str:
    """Generate a password reset token."""
    return secrets.token_urlsafe(32)


# =============================================================================
# OAuth Helpers
# =============================================================================


class OAuthHelper:
    """OAuth 2.0 token exchange for supported providers."""

    def __init__(self, config: AuthConfig):
        self.config = config

    async def exchange_google_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange Google OAuth code for user info."""
        try:
            import httpx

            # Exchange code for tokens
            async with httpx.AsyncClient() as client:
                token_resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": self.config.google_client_id,
                        "client_secret": self.config.google_client_secret,
                        "redirect_uri": f"{self.config.oauth_redirect_base}/google",
                        "grant_type": "authorization_code",
                    },
                )
                if token_resp.status_code != 200:
                    return None

                tokens = token_resp.json()

                # Get user info
                user_resp = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                )
                if user_resp.status_code != 200:
                    return None

                user_data = user_resp.json()
                return {
                    "provider": "google",
                    "provider_user_id": user_data["id"],
                    "email": user_data.get("email"),
                    "name": user_data.get("name"),
                    "avatar": user_data.get("picture"),
                    "access_token": tokens.get("access_token"),
                    "refresh_token": tokens.get("refresh_token"),
                }

        except Exception as e:
            logger.error(f"Google OAuth exchange failed: {e}")
            return None

    async def exchange_github_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange GitHub OAuth code for user info."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                token_resp = await client.post(
                    "https://github.com/login/oauth/access_token",
                    data={
                        "code": code,
                        "client_id": self.config.github_client_id,
                        "client_secret": self.config.github_client_secret,
                    },
                    headers={"Accept": "application/json"},
                )
                if token_resp.status_code != 200:
                    return None

                tokens = token_resp.json()
                access_token = tokens.get("access_token")
                if not access_token:
                    return None

                # Get user info
                user_resp = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"token {access_token}"},
                )
                user_data = user_resp.json()

                # Get email (may be private)
                email_resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"token {access_token}"},
                )
                emails = email_resp.json()
                primary_email = next(
                    (e["email"] for e in emails if e.get("primary")),
                    user_data.get("email"),
                )

                return {
                    "provider": "github",
                    "provider_user_id": str(user_data["id"]),
                    "email": primary_email,
                    "name": user_data.get("name") or user_data.get("login"),
                    "avatar": user_data.get("avatar_url"),
                    "access_token": access_token,
                    "refresh_token": None,
                }

        except Exception as e:
            logger.error(f"GitHub OAuth exchange failed: {e}")
            return None

    async def exchange_microsoft_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange Microsoft OAuth code for user info."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                token_resp = await client.post(
                    "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                    data={
                        "code": code,
                        "client_id": self.config.microsoft_client_id,
                        "client_secret": self.config.microsoft_client_secret,
                        "redirect_uri": f"{self.config.oauth_redirect_base}/microsoft",
                        "grant_type": "authorization_code",
                        "scope": "openid email profile",
                    },
                )
                if token_resp.status_code != 200:
                    return None

                tokens = token_resp.json()

                user_resp = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                )
                user_data = user_resp.json()

                return {
                    "provider": "microsoft",
                    "provider_user_id": user_data["id"],
                    "email": user_data.get("mail") or user_data.get("userPrincipalName"),
                    "name": user_data.get("displayName"),
                    "avatar": None,
                    "access_token": tokens.get("access_token"),
                    "refresh_token": tokens.get("refresh_token"),
                }

        except Exception as e:
            logger.error(f"Microsoft OAuth exchange failed: {e}")
            return None

    def get_oauth_url(self, provider: str) -> Optional[str]:
        """Get the OAuth authorization URL for a provider."""
        if provider == "google":
            return (
                "https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={self.config.google_client_id}"
                f"&redirect_uri={self.config.oauth_redirect_base}/google"
                "&response_type=code"
                "&scope=openid+email+profile"
                "&access_type=offline"
            )
        elif provider == "github":
            return (
                "https://github.com/login/oauth/authorize?"
                f"client_id={self.config.github_client_id}"
                "&scope=user:email"
            )
        elif provider == "microsoft":
            return (
                "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
                f"client_id={self.config.microsoft_client_id}"
                f"&redirect_uri={self.config.oauth_redirect_base}/microsoft"
                "&response_type=code"
                "&scope=openid+email+profile"
            )
        return None


oauth_helper = OAuthHelper(_config)
