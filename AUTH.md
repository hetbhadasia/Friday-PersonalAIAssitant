# F.R.I.D.A.Y. Authentication & Scoped Authorization

## 1. Authentication Engine

F.R.I.D.A.Y. secures its HTTP REST APIs and LiveKit WebRTC rooms via `friday.core.auth.AuthManager`:

- **Identity Carrier:** Signed JSON Web Tokens (JWT) or secure bearer tokens.
- **Claims Schema:**
  ```json
  {
    "sub": "user_iron_man",
    "scopes": ["booking:read", "booking:create", "booking:cancel", "admin:diagnostics"],
    "iat": 1718000000,
    "exp": 1718086400
  }
  ```

---

## 2. Permission Scopes

Granular permission scopes defined in `PermissionScope`:

| Scope | Description | Associated Endpoints / Actions |
|:---|:---|:---|
| `booking:read` | Read booking history and status | `GET /api/v1/bookings`, `GET /api/v1/bookings/{id}` |
| `booking:create` | Initiate new bookings and orders | `POST /api/v1/bookings`, MCP booking tools |
| `booking:cancel` | Cancel existing confirmed bookings | `POST /api/v1/bookings/{id}/cancel`, `cancel_booking` tool |
| `payment:create` | Create payment checkout sessions | `POST /api/v1/payments` |
| `admin:diagnostics` | Access health, telemetry, & metrics | `/health`, `/metrics`, `check_system_health` tool |

---

## 3. IDOR Defense (Insecure Direct Object Reference)

Every order and user resource mutation checks ownership against the authenticated identity:

```python
from friday.core.auth import auth_manager

# Verifies that current user owns the order or has admin credentials
auth_manager.verify_resource_ownership(
    user=current_authenticated_user,
    resource_owner_id=order.user_id
)
```

Cross-tenant access attempts immediately raise `PermissionDeniedError` and return HTTP 403 Forbidden.

## 4. Email OTP and Google Sign-In

The web app supports local passwordless email sign-up/sign-in and Google OAuth through Supabase. Email OTP verification, local sessions, LiveKit token generation, and signed-in conversation storage use the token server and SQLite. Google OAuth redirects through Supabase, whose returned access token is validated server-side before a local app session is issued.

Google users are matched to local accounts by their verified email address, so an existing email-OTP account can also use Google if both use the same address. Existing Supabase identities are not imported until they sign in with Google.

The token server creates six-digit codes that expire after 10 minutes, stores only a salted PBKDF2 hash, and limits verification attempts. Access and refresh tokens are random, stored as hashes, and rotated when refreshed. Authentication data is kept in `.friday_data/auth.sqlite3` by default; override this with `FRIDAY_AUTH_DB_PATH`.

Configure an SMTP sender in the token server's `.env` for email OTP:

```env
# SMTP email
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=
```

For Gmail, use an App Password rather than your normal account password. Keep SMTP credentials on the server; never put them in `VITE_*` variables or commit them.

If SMTP is not configured, code requests return an explicit configuration error. The token server applies per-IP and per-recipient limits to OTP requests and per-IP limits to verification attempts.

### Configure Google OAuth

1. In Google Cloud Console, create an OAuth 2.0 Client ID with application type **Web application**.
2. In Google Cloud's **Authorized redirect URIs**, add the Supabase callback URL shown on the Supabase Google provider page: `https://<project-ref>.supabase.co/auth/v1/callback`.
3. Paste the Google Client ID and Client Secret into Supabase **Authentication → Providers → Google** and enable the provider.
4. In Supabase **Authentication → URL Configuration**, add the frontend origin (for local development, `http://localhost:5173`) to the redirect URL allowlist.
5. In the project `.env`, set `SUPABASE_URL` to the project root URL and `SUPABASE_API_KEY` to its **publishable** key (or legacy **anon** key). Never use a service-role key here. The app reads this public key from `/api/config`; it is not a secret.
6. Restart the token server and frontend after configuration.

The app's Google button starts Supabase OAuth and returns to the current frontend origin. The token server refuses to expose a service-role key through public configuration and requires Supabase to confirm the Google email.

## 5. Signed-In Conversation Storage

Signed-in conversations are saved in the same local SQLite database and scoped by the authenticated user ID. Guest conversations remain in browser storage. Unlike the former Supabase-backed setup, this local database is not synchronized across devices; back up `.friday_data/auth.sqlite3` securely. Existing conversations stored in Supabase are not automatically imported.
