# F.R.I.D.A.Y. Automated Test Suites & Regression Verification

## 1. Test Suite Architecture

F.R.I.D.A.Y. provides three distinct test suites covering 100% of critical paths across legacy baseline, actions, and security mechanisms:

| Test Suite | File Path | Focus Area | Tests | Status |
|:---|:---|:---|:---:|:---:|
| **Baseline Core** | `tests/run_tests.py` | Config, memory fallback, tasks, confirmations | 8 | **PASS** (100%) |
| **Actions Domain** | `tests/test_actions.py` | Train, flight, movie, hotel providers, payment | 6 | **PASS** (100%) |
| **V3 State & Security**| `tests/test_v3_state_and_security.py` | State machine, SHA-256 confirmation, idempotency, webhook HMAC, reconciliation, auth, injection defense | 10 | **PASS** (100%) |
| **Frontend TypeScript**| `cd frontend && npm run build` | Vite build, React components, Lucide icons | Build | **PASS** (0 errors) |

---

## 2. Running All Tests

### Complete Backend Regression:
```bash
# Run baseline tests
uv run python tests/run_tests.py

# Run actions domain tests
uv run python tests/test_actions.py

# Run V3 state machine & security tests
uv run python tests/test_v3_state_and_security.py
```

### Complete Frontend Verification:
```bash
cd frontend && npm run build
```

---

## 3. Verified Safety Assertions

1. **State Machine Integrity:**
   - Sequential transitions succeed (`DRAFT` → `OPTION_SELECTED` → ... → `CONFIRMED`).
   - Direct illegal transitions (`DRAFT` → `CONFIRMED`) raise `StateTransitionError`.

2. **Idempotency & Replay:**
   - Repeated webhook events with same `event_id` are ignored.
   - Repeated booking operations with same `idempotency_key` return cached results without duplicate processing.

3. **Reconciliation & Zero Double-Charge:**
   - Booking provider timeout enters `UNKNOWN` state without charging again.
   - Background reconciliation confirms or transitions to `REFUND_PENDING`.

4. **Security & Sanitization:**
   - System prompts and overrides defanged.
   - Untrusted strings wrapped in boundary tags.
