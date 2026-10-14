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
