# Google Login — Frontend Integration Plan

## Context

Backend Google OAuth is **fully implemented** via `auth-fastapi` package but the project001 frontend has **zero auth UI**. User requested: "google login'i ekle, frontend'e buton koy."

**Backend state (ready):**
- Auth router mounted at `/auth` when `JWT_SECRET` (>=32 chars) + `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` are set
- `GET /auth/login/google` → redirects to Google consent screen
- `GET /auth/callback/google` → exchanges code, creates/finds user, issues JWT, redirects to:
  ```
  {FRONTEND_URL}#oauth-callback&access_token=...&refresh_token=...&expires_in=...&user={json}
  ```
- `GET /auth/me` → returns current user (requires Bearer token)
- `POST /auth/refresh` → refresh access token

**Frontend state (nothing):**
- Simple tab-based SPA (`App.vue`), no router, no Pinia, no auth state
- `apiService` has `setAuthToken(token)` / `clearAuthToken()` methods
- Vite proxy: port 20159 → backend 10159

---

## Implementation

### Step 1: Add auth composable — `frontend/src/composables/useAuth.ts`

Lightweight reactive auth state (no Pinia needed for this simple app):

```typescript
// Reactive state
const user = ref<User | null>(null)
const accessToken = ref<string | null>(null)
const refreshToken = ref<string | null>(null)
const isAuthenticated = computed(() => !!accessToken.value)

// Functions:
// - initAuth(): check localStorage for saved tokens, set on apiService
// - handleOAuthCallback(): parse hash fragment, extract tokens/user, save to localStorage
// - loginWithGoogle(): window.location.href = '/auth/login/google'
// - logout(): clear tokens from localStorage + apiService + state
// - refreshAccessToken(): POST /auth/refresh with refresh_token
```

localStorage keys: `cb_access_token`, `cb_refresh_token`, `cb_user`

### Step 2: Parse OAuth hash on app load — `frontend/src/App.vue`

In `onMounted`:
1. Check if `window.location.hash` contains `oauth-callback`
2. If yes → call `handleOAuthCallback()` → strip hash from URL
3. Otherwise → call `initAuth()` to restore saved session

### Step 3: Add Login/User UI to header — `frontend/src/App.vue`

In the existing header (right side, next to theme toggle):
- **Not authenticated:** "Login with Google" button
- **Authenticated:** User avatar/name + "Logout" button

Minimal styling consistent with existing header (flex, gap, rounded button).

### Step 4: Wire apiService token on init — `frontend/src/services/api.ts`

No changes needed — `apiService.setAuthToken()` already exists. The composable calls it.

### Step 5: Set `FRONTEND_URL` env var

Backend needs `FRONTEND_URL=http://localhost:20159` so the callback redirects to the correct frontend.

---

## Files

| Action | File | Change |
|--------|------|--------|
| CREATE | `frontend/src/composables/useAuth.ts` | Auth composable with reactive state, OAuth callback parser, login/logout |
| MODIFY | `frontend/src/App.vue` | Hash callback handling in onMounted, login/user UI in header |
| CREATE | `frontend/.env.example` | Document required env vars (GOOGLE_CLIENT_ID, etc.) |

---

## Verification

1. Set env vars: `JWT_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `FRONTEND_URL=http://localhost:20159`
2. Start backend + frontend
3. Click "Login with Google" → redirected to Google → authorize → redirected back with tokens in hash
4. Header shows user name, "Logout" button
5. Refresh page → still logged in (localStorage)
6. Click "Logout" → back to "Login with Google" button
7. `curl -H "Authorization: Bearer {token}" localhost:10159/auth/me` → returns user
