# Genesis Auth Library - Design Document

**Date:** 2026-02-10
**Status:** DRAFT
**Scope:** Shared auth library for all Genesis subprojects

---

## 1. Problem

- Project001 Etsy tokens in-memory only, lost on restart
- No user identity in project001 (single anonymous session)
- cigkoftecibey-webapp has its own auth copy
- Future subprojects will need the same auth pattern
- Genesis Core has good auth but tightly coupled to its own domain

## 2. Decision

Shared monorepo package `packages/genesis-auth/` with:
- Google OAuth (PKCE + OpenID Connect)
- JWT issue/verify/refresh
- Abstract base models (User, Session, ProviderToken)
- Fernet-encrypted provider token storage (Etsy, GitHub, Drive, etc.)
- FastAPI-ready router + dependencies

## 3. Package Structure

```
packages/genesis-auth/
├── pyproject.toml
├── genesis_auth/
│   ├── __init__.py                ← Public API: AuthConfig, GoogleAuth, JWTService, etc.
│   ├── config.py                  ← AuthConfig dataclass
│   ├── google.py                  ← GoogleAuthProvider (Authlib)
│   ├── jwt.py                     ← JWTService (PyJWT, HS256)
│   ├── models.py                  ← UserBase, SessionBase, ProviderTokenBase (__abstract__)
│   ├── encryption.py              ← TokenEncryption (Fernet)
│   ├── providers.py               ← ProviderTokenManager (CRUD + auto-refresh)
│   ├── exceptions.py              ← AuthError hierarchy
│   ├── fastapi/
│   │   ├── __init__.py
│   │   ├── dependencies.py        ← get_current_user, require_auth, get_optional_user
│   │   └── routes.py              ← create_auth_router() factory
│   └── _compat.py                 ← SQLAlchemy 1.4/2.0 compatibility helpers
└── tests/
    ├── conftest.py                ← In-memory SQLite fixtures
    ├── test_jwt.py
    ├── test_google.py
    ├── test_encryption.py
    ├── test_providers.py
    └── test_fastapi_routes.py
```

## 4. Core Components

### 4.1 AuthConfig

```python
@dataclass
class AuthConfig:
    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "/auth/callback/google"
    google_scopes: list[str] = field(default_factory=lambda: ["openid", "email", "profile"])

    # JWT
    jwt_secret: str = ""           # Auto-generated in dev if empty
    jwt_algorithm: str = "HS256"
    access_token_ttl: int = 900    # 15 min
    refresh_token_ttl: int = 604800  # 7 days

    # Encryption
    encryption_key: str = ""       # Fernet key, auto-generated in dev if empty

    # Behavior
    auto_create_users: bool = True  # Create user on first Google login
    token_rotation: bool = True     # Rotate refresh tokens on use
```

### 4.2 Models (Abstract Bases)

```python
class UserBase(DeclarativeBase):
    """Extend in consumer: class User(UserBase): __tablename__ = 'users'"""
    __abstract__ = True

    id            = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email         = Column(String(255), unique=True, index=True, nullable=False)
    name          = Column(String(255), nullable=False)
    avatar_url    = Column(String(512), nullable=True)
    provider      = Column(String(20), nullable=False)     # "google"
    provider_id   = Column(String(255), nullable=False)    # Google sub
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


class SessionBase(DeclarativeBase):
    __abstract__ = True

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    user_id            = Column(String(36), index=True, nullable=False)
    refresh_token_hash = Column(String(255), nullable=False)
    ip_address         = Column(String(45), nullable=True)
    user_agent         = Column(String(512), nullable=True)
    expires_at         = Column(DateTime, nullable=False)
    is_revoked         = Column(Boolean, default=False)
    created_at         = Column(DateTime, default=datetime.utcnow)


class ProviderTokenBase(DeclarativeBase):
    """One row per (user, provider). Tokens encrypted at rest."""
    __abstract__ = True

    id                       = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id                  = Column(String(36), index=True, nullable=False)
    provider                 = Column(String(20), nullable=False)
    encrypted_access_token   = Column(LargeBinary, nullable=False)
    encrypted_refresh_token  = Column(LargeBinary, nullable=True)
    scopes                   = Column(JSON, nullable=True)
    expires_at               = Column(DateTime, nullable=True)
    provider_metadata        = Column(JSON, nullable=True)  # shop_id, username, etc.
    created_at               = Column(DateTime, default=datetime.utcnow)
    updated_at               = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "provider"),)
```

### 4.3 GoogleAuthProvider

```python
class GoogleAuthProvider:
    def __init__(self, config: AuthConfig):
        self.oauth = OAuth()
        self.oauth.register(
            name="google",
            client_id=config.google_client_id,
            client_secret=config.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": " ".join(config.google_scopes), "code_challenge_method": "S256"},
        )

    async def get_auth_url(self, request, redirect_uri: str, state: str | None = None) -> str:
        """Generate Google consent URL with PKCE."""

    async def handle_callback(self, request) -> GoogleUser:
        """Exchange code, verify nonce, return GoogleUser(email, name, picture, sub)."""

    async def verify_id_token(self, credential: str) -> GoogleUser:
        """Verify a Google ID token (for mobile/SPA one-tap flows)."""
```

### 4.4 JWTService

```python
class JWTService:
    def __init__(self, config: AuthConfig): ...

    def create_access_token(self, user_id: str, email: str, extra_claims: dict = None) -> str:
        """Short-lived (15min). Payload: sub, email, type=access, exp, iat + extra_claims."""

    def create_refresh_token(self, user_id: str) -> str:
        """Long-lived (7day). Payload: sub, type=refresh, exp, iat."""

    def verify_token(self, token: str, expected_type: str = "access") -> TokenPayload:
        """Verify signature + expiry + type. Raises TokenExpired or InvalidToken."""

    def create_token_pair(self, user_id: str, email: str) -> TokenPair:
        """Convenience: returns TokenPair(access_token, refresh_token)."""
```

### 4.5 TokenEncryption

```python
class TokenEncryption:
    def __init__(self, key: str): ...

    def encrypt(self, plaintext: str) -> bytes:
        """Fernet encrypt. Returns bytes for LargeBinary column."""

    def decrypt(self, ciphertext: bytes) -> str:
        """Fernet decrypt. Raises EncryptionError if key mismatch."""

    @staticmethod
    def generate_key() -> str:
        """Generate new Fernet key for .env setup."""
```

### 4.6 ProviderTokenManager

```python
class ProviderTokenManager:
    def __init__(self, encryption: TokenEncryption, db_session_factory): ...

    async def store_tokens(
        self, user_id: str, provider: str,
        access_token: str, refresh_token: str | None = None,
        scopes: list[str] = None, expires_at: datetime = None,
        metadata: dict = None
    ) -> None:
        """Encrypt + upsert provider tokens for user."""

    async def get_tokens(self, user_id: str, provider: str) -> ProviderTokens | None:
        """Decrypt + return tokens. Returns None if not linked."""

    async def delete_tokens(self, user_id: str, provider: str) -> None:
        """Unlink provider (revoke). Deletes row."""

    async def refresh_if_expired(
        self, user_id: str, provider: str,
        refresh_fn: Callable[[str], Awaitable[TokenRefreshResult]]
    ) -> ProviderTokens:
        """Check expiry, call refresh_fn if needed, update DB, return fresh tokens."""

    async def list_providers(self, user_id: str) -> list[ProviderInfo]:
        """List linked providers for user profile display."""
```

### 4.7 FastAPI Integration

```python
# genesis_auth/fastapi/routes.py

def create_auth_router(
    config: AuthConfig,
    user_model: type,           # Consumer's concrete User class
    session_model: type,        # Consumer's concrete Session class
    db_dependency: Callable,    # Consumer's Depends(get_db)
) -> APIRouter:
    """
    Returns a router with these endpoints:

    GET  /auth/google              → Redirect to Google consent
    GET  /auth/callback/google     → Handle callback, issue JWT, redirect to frontend
    POST /auth/refresh             → Rotate refresh token
    POST /auth/logout              → Revoke session
    GET  /auth/me                  → Current user profile
    GET  /auth/providers           → List linked providers (etsy, drive, etc.)
    """


# genesis_auth/fastapi/dependencies.py

def create_auth_dependencies(config: AuthConfig, user_model: type, db_dependency: Callable):
    """Returns a dict of dependency functions."""

    async def get_current_user(...) -> user_model:
        """Extract JWT from Authorization header, verify, fetch user from DB.
        Raises 401 if missing/invalid/expired."""

    async def get_optional_user(...) -> user_model | None:
        """Same but returns None for anonymous. For public endpoints."""

    async def require_auth(...) -> user_model:
        """Alias for get_current_user. Semantic clarity."""

    return {
        "get_current_user": get_current_user,
        "get_optional_user": get_optional_user,
        "require_auth": require_auth,
    }
```

### 4.8 Exception Hierarchy

```python
class AuthError(Exception): ...
class InvalidToken(AuthError): ...
class TokenExpired(AuthError): ...
class ProviderError(AuthError): ...
class ProviderNotLinked(ProviderError): ...
class ProviderTokenExpired(ProviderError): ...
class EncryptionError(AuthError): ...
class GoogleAuthError(AuthError): ...
```

## 5. Consumer Integration Pattern

### 5.1 Project001 (Coloring Book)

```python
# src/coloring_book/auth/models.py
from genesis_auth.models import UserBase, SessionBase, ProviderTokenBase

class User(UserBase):
    __tablename__ = "users"
    favorite_theme = Column(String, nullable=True)

class Session(SessionBase):
    __tablename__ = "sessions"
    user_id = Column(String, ForeignKey("users.id"))

class ProviderToken(ProviderTokenBase):
    __tablename__ = "provider_tokens"
    user_id = Column(String, ForeignKey("users.id"))


# src/coloring_book/api/app.py
from genesis_auth import AuthConfig
from genesis_auth.fastapi import create_auth_router, create_auth_dependencies

auth_config = AuthConfig(
    google_client_id=os.getenv("GOOGLE_CLIENT_ID"),
    google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    jwt_secret=os.getenv("JWT_SECRET"),
    encryption_key=os.getenv("TOKEN_ENCRYPTION_KEY"),
)

auth_router = create_auth_router(auth_config, User, Session, get_db)
auth_deps = create_auth_dependencies(auth_config, User, get_db)
get_current_user = auth_deps["get_current_user"]

app.include_router(auth_router)


# src/coloring_book/api/etsy_routes.py  (updated)
@router.post("/etsy/connect")
async def connect_etsy(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start Etsy OAuth - user-specific."""
    etsy_client = EtsyClient(api_key=ETSY_API_KEY, api_secret=ETSY_API_SECRET)
    url, state = etsy_client.get_auth_url()
    # Store state in user's session for CSRF validation
    return {"auth_url": url, "state": state}


@router.post("/etsy/callback")
async def etsy_callback(
    code: str, state: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exchange Etsy code, encrypt+store tokens per user."""
    etsy_client = EtsyClient(api_key=ETSY_API_KEY, api_secret=ETSY_API_SECRET)
    tokens = await etsy_client.exchange_code(code)

    # Store encrypted via genesis-auth
    token_mgr = ProviderTokenManager(encryption, db)
    await token_mgr.store_tokens(
        user_id=user.id,
        provider="etsy",
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        scopes=["listings_w", "listings_r", "shops_r"],
        expires_at=tokens.expires_at,
        metadata={"shop_id": shop.shop_id},  # from get_shop()
    )
    return {"connected": True}


@router.post("/workbooks/{id}/publish")
async def publish_workbook(
    id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Publish using THIS user's Etsy tokens."""
    token_mgr = ProviderTokenManager(encryption, db)
    etsy_tokens = await token_mgr.get_tokens(user.id, "etsy")
    if not etsy_tokens:
        raise HTTPException(401, "Connect your Etsy account first")

    # Auto-refresh if expired
    etsy_tokens = await token_mgr.refresh_if_expired(
        user.id, "etsy",
        refresh_fn=etsy_client.refresh_token
    )

    etsy_client = EtsyClient(api_key=ETSY_API_KEY, api_secret=ETSY_API_SECRET)
    etsy_client.tokens = etsy_tokens.to_token_response()
    result = await etsy_client.create_draft_listing(...)
    return result
```

### 5.2 cigkoftecibey-webapp (Migration Path)

```python
# Mevcut User modeline UserBase mixin olarak ekle
# veya mevcut tabloyu koru, sadece Session + ProviderToken ekle
# Migration: yeni kolonlar + veri tasima (google_id → provider_id)
```

### 5.3 Future Project (e.g., genesis-drive-exporter)

```python
from genesis_auth.fastapi import create_auth_router, create_auth_dependencies
# 5 satir setup, auth hazir
# ProviderTokenManager ile Drive token'lari da yonetilebilir
```

## 6. Frontend Auth Flow

### 6.1 Login Flow

```
1. User clicks "Sign in with Google"
2. Frontend redirects to: GET /auth/google
3. Backend redirects to Google consent screen
4. User approves → Google redirects to: GET /auth/callback/google
5. Backend:
   a. Exchange code for Google tokens
   b. Extract user info (email, name, picture)
   c. Create/update User in DB
   d. Issue JWT access + refresh tokens
   e. Redirect to frontend: /#token=<access>&refresh=<refresh>
6. Frontend:
   a. Parse tokens from URL fragment (never hits server logs)
   b. Store access_token in memory (reactive ref)
   c. Store refresh_token in httpOnly cookie OR localStorage
   d. Fetch user profile: GET /auth/me
   e. Render authenticated UI
```

### 6.2 Frontend Auth Store (Vue 3 Composable)

```typescript
// frontend/src/composables/useAuth.ts
export function useAuth() {
  const user = ref<AuthUser | null>(null)
  const token = ref<string | null>(null)
  const isAuthenticated = computed(() => !!token.value && !!user.value)

  function login() {
    window.location.href = `${API_BASE}/auth/google`
  }

  function handleCallback() {
    // Parse token from URL fragment after redirect
    const hash = new URLSearchParams(window.location.hash.substring(1))
    token.value = hash.get('token')
    refreshToken = hash.get('refresh')
    localStorage.setItem('refresh_token', refreshToken)
    window.location.hash = ''  // Clean URL
    fetchUser()
  }

  async function fetchUser() {
    user.value = await apiService.get('/auth/me')
  }

  async function refreshAccessToken() {
    const refresh = localStorage.getItem('refresh_token')
    const resp = await apiService.post('/auth/refresh', { refresh_token: refresh })
    token.value = resp.access_token
    localStorage.setItem('refresh_token', resp.refresh_token)
  }

  function logout() {
    apiService.post('/auth/logout', { refresh_token: localStorage.getItem('refresh_token') })
    token.value = null
    user.value = null
    localStorage.removeItem('refresh_token')
  }

  // Auto-refresh: intercept 401 → refresh → retry
  apiService.interceptors.response(async (error) => {
    if (error.status === 401 && !error.config._retry) {
      error.config._retry = true
      await refreshAccessToken()
      return apiService.request(error.config)
    }
    throw error
  })

  return { user, token, isAuthenticated, login, logout, handleCallback, refreshAccessToken }
}
```

### 6.3 Etsy Connection UI

```
Authenticated user's profile/settings page:
┌─────────────────────────────────────┐
│  Connected Accounts                  │
│                                      │
│  ● Google   okan@gmail.com    ✓     │
│  ○ Etsy     Not connected  [Link]   │
│                                      │
│  [Link] → opens Etsy OAuth popup    │
│  After callback → ● Etsy  shop123 ✓ │
└─────────────────────────────────────┘
```

## 7. Security Considerations

| Concern | Solution |
|---------|----------|
| Token at rest | Fernet encryption (AES-128-CBC + HMAC) |
| JWT secret | Env var, auto-generated in dev |
| CSRF | State parameter in OAuth, SameSite cookies |
| PKCE | SHA256 code challenge for both Google and Etsy |
| Refresh token theft | Rotation on use, bcrypt hash in DB |
| XSS token leak | Access token in memory only (not localStorage) |
| Session fixation | Clear session data before issuing tokens |
| Privilege escalation | Provider tokens scoped per-user, never shared |

## 8. Dependencies

```toml
[project]
name = "genesis-auth"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "authlib>=1.3.0",         # Google OAuth + PKCE
    "PyJWT>=2.8.0",           # JWT encode/decode
    "cryptography>=41.0.0",   # Fernet encryption
    "bcrypt>=4.1.0",          # Refresh token hashing
    "sqlalchemy>=2.0.0",      # Base models
    "httpx>=0.25.0",          # Async HTTP for token exchange
]

[project.optional-dependencies]
fastapi = [
    "fastapi>=0.100.0",
    "python-multipart>=0.0.6",
]
```

## 9. Testing Strategy

| Layer | Tests | Method |
|-------|-------|--------|
| JWT | issue, verify, expire, tamper, rotate | Unit (no DB) |
| Encryption | encrypt/decrypt, key rotation, wrong key | Unit (no DB) |
| Google OAuth | auth URL, callback, ID token verify | Unit (mock Authlib) |
| ProviderTokenManager | store, get, refresh, delete, list | Integration (in-memory SQLite) |
| FastAPI routes | /auth/google, /callback, /me, /refresh, /logout | Integration (TestClient) |
| Consumer integration | Project001 full flow | E2E |

## 10. Implementation Phases

### Phase 1: Core Library (foundation)
- AuthConfig, JWTService, TokenEncryption, exceptions
- Abstract base models
- Unit tests (JWT + encryption)

### Phase 2: Google OAuth + FastAPI
- GoogleAuthProvider with Authlib
- create_auth_router() factory
- get_current_user dependency
- Route tests with TestClient

### Phase 3: Provider Token Management
- ProviderTokenManager (CRUD + auto-refresh)
- Integration tests with in-memory SQLite

### Phase 4: Project001 Integration
- User/Session/ProviderToken concrete models
- Alembic migration for users, sessions, provider_tokens tables
- Mount auth_router in app.py
- Migrate etsy_routes to per-user tokens
- Frontend useAuth composable
- Update EtsyPublisher UI with login gate

### Phase 5: Genesis Core Migration (optional, later)
- Replace inline auth with genesis-auth
- Preserve existing user data

## 11. Environment Variables (Consumer)

```bash
# Google OAuth (required)
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx

# JWT (auto-generated in dev)
JWT_SECRET=your-256-bit-secret

# Token Encryption (auto-generated in dev)
TOKEN_ENCRYPTION_KEY=your-fernet-key

# Existing Etsy keys (unchanged)
ETSY_API_KEY=xxx
ETSY_API_SECRET=xxx
```

## 12. Migration: Existing Etsy Flow → Per-User

| Before | After |
|--------|-------|
| Global `_etsy_client` singleton | Per-request EtsyClient with user's tokens |
| Tokens in memory | Encrypted in provider_tokens table |
| Single user, lost on restart | Multi-user, persistent |
| No auth on endpoints | JWT-protected, user-scoped |
| `GET /etsy/auth-url` (anonymous) | `POST /etsy/connect` (authenticated) |
| `POST /etsy/callback` (global) | `POST /etsy/callback` (user-scoped) |
