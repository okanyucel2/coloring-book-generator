# Genesis Auth - Phase 1: Core Library Foundation

## Context

Project001 needs user authentication (Google OAuth) and per-user Etsy token management. Rather than building from scratch, we extend the **existing** `packages/auth-core` and `packages/auth-flows` packages that already provide JWT, Google ID token verification, session management, and SQLAlchemy mixins.

**What already exists:**
- `auth-core` v1.0.0: `create_access_token()`, `decode_token()`, `verify_google_token()`, password hashing
- `auth-flows` v1.0.0: `SessionManager`, `SessionMixin`, token utilities (`hash_token`, `verify_token_hash`)

**What's missing for our design:**
1. Fernet encryption for provider tokens (Etsy/GitHub/Drive)
2. Typed JWT tokens (access vs refresh, with `create_token_pair()`)
3. `UserMixin` (base user model with Google/provider fields)
4. `ProviderTokenMixin` (encrypted provider token storage)
5. `ProviderTokenManager` (CRUD + auto-refresh for provider tokens)

Phase 1 adds items 1-5 to the existing packages. Phase 2 (future) adds FastAPI integration (`auth-fastapi` package).

---

## Implementation Plan

### Step 1: Enhance auth-core v1.1.0

**File: `packages/auth-core/src/auth_core/encryption.py`** (NEW)

```python
class TokenEncryption:
    """Fernet-based encryption for provider tokens at rest."""
    def __init__(self, key: str): ...
    def encrypt(self, plaintext: str) -> bytes: ...
    def decrypt(self, ciphertext: bytes) -> str: ...
    @staticmethod
    def generate_key() -> str: ...
```

- Uses `cryptography.fernet.Fernet` (AES-128-CBC + HMAC-SHA256)
- Key from env var or auto-generated in dev
- Raises `EncryptionError` on key mismatch

**File: `packages/auth-core/src/auth_core/jwt_manager.py`** (MODIFY)

Add `create_token_pair()` function:
```python
def create_token_pair(
    user_id: str,
    email: str,
    secret: str,
    access_ttl: timedelta = timedelta(minutes=15),
    refresh_ttl: timedelta = timedelta(days=7),
    extra_claims: dict = None,
) -> dict:
    """Returns {access_token, refresh_token, token_type, expires_in}"""
```

Add `verify_typed_token()` that validates `type` field in payload.

**File: `packages/auth-core/src/auth_core/exceptions.py`** (MODIFY)

Add:
```python
class EncryptionError(AuthCoreError): ...
class ProviderError(AuthCoreError): ...
class ProviderNotLinkedError(ProviderError): ...
class ProviderTokenExpiredError(ProviderError): ...
```

**File: `packages/auth-core/src/auth_core/__init__.py`** (MODIFY)

Export new symbols: `TokenEncryption`, `create_token_pair`, `verify_typed_token`, new exceptions.

**File: `packages/auth-core/pyproject.toml`** (MODIFY)

- Bump version to 1.1.0
- Add `cryptography>=41.0.0` to dependencies

### Step 2: Enhance auth-flows v1.1.0

**File: `packages/auth-flows/src/auth_flows/models.py`** (MODIFY)

Add two new mixins:

```python
class UserMixin:
    """Base user model mixin with OAuth provider fields.
    Usage: class User(Base, UserMixin): __tablename__ = 'users'"""
    id: "Mapped[str]"              # UUID
    email: "Mapped[str]"           # Unique, indexed
    name: "Mapped[str]"
    avatar_url: "Mapped[str | None]"
    provider: "Mapped[str]"        # "google"
    provider_id: "Mapped[str]"     # Google sub ID
    is_active: "Mapped[bool]"
    created_at: "Mapped[datetime]"
    last_login_at: "Mapped[datetime | None]"

class ProviderTokenMixin:
    """Encrypted provider token storage mixin.
    Usage: class ProviderToken(Base, ProviderTokenMixin): __tablename__ = 'provider_tokens'"""
    id: "Mapped[str]"                        # UUID
    user_id: "Mapped[str]"                   # FK to users
    provider: "Mapped[str]"                  # "etsy", "github", "drive"
    encrypted_access_token: "Mapped[bytes]"  # Fernet encrypted
    encrypted_refresh_token: "Mapped[bytes | None]"
    scopes: "Mapped[dict | None]"            # JSON
    expires_at: "Mapped[datetime | None]"
    provider_metadata: "Mapped[dict | None]" # JSON (shop_id etc.)
    created_at: "Mapped[datetime]"
    updated_at: "Mapped[datetime | None]"
```

**File: `packages/auth-flows/src/auth_flows/provider_tokens.py`** (NEW)

```python
class ProviderTokenManager:
    """CRUD + auto-refresh for encrypted provider tokens."""
    def __init__(self, encryption: TokenEncryption, session_factory): ...
    async def store_tokens(self, user_id, provider, access_token, refresh_token, ...): ...
    async def get_tokens(self, user_id, provider) -> ProviderTokens | None: ...
    async def delete_tokens(self, user_id, provider): ...
    async def refresh_if_expired(self, user_id, provider, refresh_fn): ...
    async def list_providers(self, user_id) -> list[ProviderInfo]: ...
```

- Encrypts before write, decrypts after read
- `refresh_if_expired` takes a callable `refresh_fn(refresh_token) -> new_tokens`
- Upsert pattern: one row per (user_id, provider)

**File: `packages/auth-flows/src/auth_flows/__init__.py`** (MODIFY)

Export: `UserMixin`, `ProviderTokenMixin`, `ProviderTokenManager`, `ProviderTokens`, `ProviderInfo`.

**File: `packages/auth-flows/pyproject.toml`** (MODIFY)

- Bump version to 1.1.0
- Ensure `genesis-auth-core>=1.1.0` dependency

### Step 3: Tests

**File: `packages/auth-core/tests/test_encryption.py`** (NEW)

- `test_encrypt_decrypt_roundtrip`
- `test_wrong_key_raises_error`
- `test_empty_string_encrypt`
- `test_generate_key_unique`
- `test_unicode_content`

**File: `packages/auth-core/tests/test_jwt_typed.py`** (NEW)

- `test_create_token_pair_returns_both`
- `test_access_token_has_type_field`
- `test_refresh_token_has_type_field`
- `test_verify_typed_token_wrong_type_raises`
- `test_access_token_expires_in_15min`
- `test_refresh_token_expires_in_7days`
- `test_extra_claims_included`

**File: `packages/auth-flows/tests/test_provider_tokens.py`** (NEW)

- `test_store_and_get_tokens`
- `test_get_nonexistent_returns_none`
- `test_upsert_overwrites_existing`
- `test_delete_tokens`
- `test_list_providers`
- `test_tokens_are_encrypted_in_db`
- `test_refresh_if_expired_calls_refresh_fn`
- `test_refresh_if_not_expired_returns_cached`

**File: `packages/auth-flows/tests/test_user_mixin.py`** (NEW)

- `test_user_mixin_fields_exist`
- `test_provider_token_mixin_fields_exist`
- `test_provider_token_is_expired_property`

---

## Files Summary

| Package | Action | File | Purpose |
|---------|--------|------|---------|
| auth-core | CREATE | `src/auth_core/encryption.py` | Fernet encrypt/decrypt |
| auth-core | MODIFY | `src/auth_core/jwt_manager.py` | Add `create_token_pair`, `verify_typed_token` |
| auth-core | MODIFY | `src/auth_core/exceptions.py` | Add Encryption + Provider exceptions |
| auth-core | MODIFY | `src/auth_core/__init__.py` | Export new symbols |
| auth-core | MODIFY | `pyproject.toml` | v1.1.0, add cryptography dep |
| auth-core | CREATE | `tests/test_encryption.py` | Encryption unit tests |
| auth-core | CREATE | `tests/test_jwt_typed.py` | Typed JWT unit tests |
| auth-flows | MODIFY | `src/auth_flows/models.py` | Add UserMixin + ProviderTokenMixin |
| auth-flows | CREATE | `src/auth_flows/provider_tokens.py` | ProviderTokenManager class |
| auth-flows | MODIFY | `src/auth_flows/__init__.py` | Export new symbols |
| auth-flows | MODIFY | `pyproject.toml` | v1.1.0, auth-core>=1.1.0 |
| auth-flows | CREATE | `tests/test_provider_tokens.py` | Provider token integration tests |
| auth-flows | CREATE | `tests/test_user_mixin.py` | Mixin field verification |

---

## Verification

```bash
# 1. Install updated packages
cd /Users/okan.yucel/Desktop/genesisv3
pip install -e packages/auth-core
pip install -e "packages/auth-flows[sqlalchemy]"

# 2. Run auth-core tests
cd packages/auth-core && python -m pytest tests/ -v

# 3. Run auth-flows tests
cd packages/auth-flows && python -m pytest tests/ -v

# 4. Verify existing tests still pass (no regressions)
cd packages/auth-core && python -m pytest tests/test_jwt_manager.py tests/test_google_oauth.py -v
cd packages/auth-flows && python -m pytest tests/test_session.py tests/test_tokens.py -v

# 5. Quick smoke test
python -c "
from auth_core import TokenEncryption, create_token_pair, verify_typed_token
from auth_flows import UserMixin, ProviderTokenMixin, ProviderTokenManager

# Encryption roundtrip
enc = TokenEncryption(TokenEncryption.generate_key())
assert enc.decrypt(enc.encrypt('secret')) == 'secret'

# Typed JWT
pair = create_token_pair('user-1', 'test@test.com', 'secret-key')
payload = verify_typed_token(pair['access_token'], 'secret-key', expected_type='access')
assert payload['sub'] == 'user-1'
assert payload['type'] == 'access'

print('Phase 1 smoke test PASSED')
"
```

---

## What Comes Next (NOT in this phase)

- **Phase 2:** `packages/auth-fastapi/` — `create_auth_router()`, `get_current_user` dep, Google OAuth redirect flow (Authlib)
- **Phase 3:** Project001 integration — concrete User/Session/ProviderToken models, Alembic migration, mount auth router
- **Phase 4:** Frontend `useAuth` composable + login UI
- **Phase 5:** Migrate etsy_routes to per-user tokens via ProviderTokenManager
