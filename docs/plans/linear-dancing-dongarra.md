# Etsy OAuth Completion — Genesis Infrastructure Reuse Plan

## Context

Etsy OAuth integration is ~40% complete. Backend PKCE flow works, frontend UI exists, SEO engine generates metadata. But the flow is broken end-to-end: the callback doesn't signal the frontend, tokens are in-memory (lost on restart), and shop_id is hardcoded to 0.

Genesis already has production-grade auth infrastructure:
- `DbProviderTokenManager` — encrypted token CRUD with auto-refresh (`provider_token_service.py`)
- `TokenEncryption` — Fernet AES for tokens at rest (`packages/auth-core`)
- `ProviderToken` model — multi-provider token storage with `provider_metadata` JSON column
- Google OAuth callback pattern — fragment-based redirect to frontend (`packages/auth-fastapi/router.py:196-213`)

**Goal:** Wire existing Genesis infrastructure into the Etsy OAuth flow to make it production-ready.

---

## Architecture: Before vs After

```
BEFORE (broken):
  Frontend → window.open(etsy) → Backend callback → JSON response → popup stuck
  Tokens: in-memory singleton → lost on restart
  shop_id: hardcoded 0

AFTER:
  Frontend → window.open(etsy) → Backend callback → HTML page → postMessage → popup closes
  Tokens: DbProviderTokenManager → encrypted in ProviderToken table → survive restarts
  shop_id: fetched via get_me() after auth → stored in provider_metadata
```

---

## Genesis Reuse Map

| Genesis Component | File | Reuse For |
|-------------------|------|-----------|
| `DbProviderTokenManager` | `api/provider_token_service.py` | Store/retrieve/refresh Etsy tokens |
| `TokenEncryption` | `packages/auth-core/encryption.py` | Encrypt tokens before DB storage |
| `ProviderToken` model | `api/models.py:99-114` | DB table (already exists, `provider="etsy"`) |
| Callback redirect pattern | `packages/auth-fastapi/router.py:196-213` | postMessage-based popup signal |
| `_provider_token_manager` | `api/app.py:59-62` | Already instantiated in app startup |

---

## Wave Plan

### Wave 1: Backend — Token Persistence + Callback Redirect

**Problem:** Tokens in-memory, callback returns JSON (popup stuck).

**File: `src/coloring_book/api/etsy_routes.py`**

1. **Import & inject `DbProviderTokenManager`** via `get_provider_token_manager()` from `app.py`:
   - Remove global `_etsy_state` variable
   - Add state storage per-request (use a simple dict keyed by state value, with TTL)

2. **Rewrite `/callback` endpoint** (lines 114-151):
   - Change from `POST` (JSON body) to `GET` (query params) — Etsy redirects via GET with `?code=X&state=Y`
   - After `exchange_code()`: store tokens via `DbProviderTokenManager.store_tokens(user_id="default", provider="etsy", ...)`
   - After token storage: call `client.get_me()` to fetch shop info, store `shop_id` in `provider_metadata`
   - Return an `HTMLResponse` that sends `postMessage` to opener and closes itself:
   ```python
   from fastapi.responses import HTMLResponse
   html = """<html><body><script>
     window.opener.postMessage({type:"etsy-oauth-complete",success:true,shopId:SHOP_ID},"*");
     window.close();
   </script></body></html>"""
   return HTMLResponse(content=html)
   ```

3. **Rewrite `/status` endpoint** (lines 153-163):
   - Check `DbProviderTokenManager.get_tokens("default", "etsy")` instead of in-memory client
   - Return `shop_id` from `provider_metadata`

4. **Rewrite `/disconnect` endpoint** (lines 166-171):
   - Call `DbProviderTokenManager.delete_tokens("default", "etsy")`

5. **Update publish flow** (lines 204-285):
   - Load tokens from DB before publishing
   - Set them on the EtsyClient instance
   - Use `refresh_if_expired()` for auto-refresh

6. **Fix state parameter race condition** (line 31):
   - Replace global `_etsy_state` with a dict `_pending_states: dict[str, float]` (state → timestamp)
   - Clean up expired states (>10 min) on each auth-url request

**File: `src/coloring_book/api/app.py`**
- Ensure `_provider_token_manager` is available even without Google OAuth (currently conditional on Google env vars)
- Extract encryption setup to work independently of Google auth

### Wave 2: Frontend — OAuth Window Communication + Shop ID

**File: `frontend/src/components/EtsyPublisher.vue`**

1. **Add `postMessage` listener** for OAuth completion:
   ```typescript
   onMounted(() => {
     window.addEventListener('message', handleOAuthMessage)
     checkConnection()
   })
   onUnmounted(() => {
     window.removeEventListener('message', handleOAuthMessage)
   })
   function handleOAuthMessage(event: MessageEvent) {
     if (event.data?.type === 'etsy-oauth-complete') {
       isConnected.value = event.data.success
       shopId.value = event.data.shopId
       connecting.value = false
     }
   }
   ```

2. **Fix `connectEtsy()`** (lines 149-160):
   - Keep `connecting.value = true` until `postMessage` arrives (don't set false in finally)
   - Add 5-minute timeout fallback

3. **Use real `shop_id`** (line 195):
   - Store from postMessage or fetch from `/etsy/status`
   - Replace hardcoded `shop_id: 0`

4. **Add connection indicator** with shop name:
   - Show "Connected to Shop #12345" when authenticated

### Wave 3: Make Token Manager Available Without Google Auth

**File: `src/coloring_book/api/app.py`** (lines 34-78)

Currently `DbProviderTokenManager` is only created when Google OAuth env vars are set. Etsy needs it independently.

- Extract token manager initialization to a separate block:
  ```python
  # Provider token encryption (needed for Etsy even without Google auth)
  _provider_key = os.environ.get("PROVIDER_TOKEN_KEY", "")
  if not _provider_key:
      _provider_key = TokenEncryption.generate_key()
  _token_encryption = TokenEncryption(_provider_key)
  _provider_token_manager = DbProviderTokenManager(
      encryption=_token_encryption,
      session_factory=async_session,
  )
  ```
- Move this BEFORE the Google OAuth conditional block
- `get_provider_token_manager()` returns it unconditionally

### Wave 4: Tests

**File: `tests/test_etsy_oauth_flow.py`** (NEW)

Backend tests:
- `test_callback_returns_html_response` — verify HTMLResponse with postMessage script
- `test_callback_stores_tokens_in_db` — verify ProviderToken row created
- `test_status_reads_from_db` — verify status uses DB, not in-memory
- `test_disconnect_removes_db_tokens` — verify deletion
- `test_tokens_survive_client_recreation` — simulate restart
- `test_state_race_condition` — two concurrent auth flows don't interfere

Frontend E2E (Playwright):
- `test_oauth_popup_opens` — verify window.open called
- `test_postmessage_closes_popup` — mock postMessage, verify connected state
- `test_shop_id_displayed` — verify shop ID from status

---

## Files Summary

| Action | File | Change |
|--------|------|--------|
| MODIFY | `src/coloring_book/api/app.py:34-78` | Extract token manager init before Google block |
| MODIFY | `src/coloring_book/api/etsy_routes.py` | Full rewrite: callback→GET+HTML, DB tokens, state dict |
| MODIFY | `frontend/src/components/EtsyPublisher.vue` | postMessage listener, real shop_id, connecting state |
| CREATE | `tests/test_etsy_oauth_flow.py` | Backend OAuth flow tests |
| CREATE | `frontend/e2e/etsy-oauth.spec.ts` | Playwright E2E for OAuth flow |

---

## Verification

1. **Token persistence:** Start backend → connect Etsy → restart backend → `GET /etsy/status` → still connected
2. **Callback redirect:** Click "Connect Etsy" → authorize on Etsy → popup auto-closes → frontend shows "Connected"
3. **Shop ID:** After connection, verify shop_id appears in status response and frontend publish uses it
4. **Disconnect:** Click "Disconnect" → verify `ProviderToken` row deleted → status shows disconnected
5. **Race condition:** Open two browser tabs → start OAuth in both → both complete without conflict
6. **Backend tests:** `pytest tests/test_etsy_oauth_flow.py -v` — all pass
