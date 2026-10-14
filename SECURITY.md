# F.R.I.D.A.Y. Security & Compliance Architecture

## 1. Prompt-Injection Defense Layer

Because F.R.I.D.A.Y. ingests untrusted data from external sources (e.g., RSS news, web scraping, user search queries, provider API responses), all inputs pass through `friday.core.sanitizer.Sanitizer`:

1. **Isolation Tags:** Untrusted content is wrapped in XML-style boundary delimiters:
   ```xml
   <untrusted_content source="web_search">
   ...sanitized payload...
   </untrusted_content>
   ```
2. **Instruction Neutralization:** Defangs common prompt injection phrases:
   - "Ignore previous instructions"
   - "You are now a DAN / unrestricted model"
   - "SYSTEM OVERRIDE"
3. **Escaping:** Control characters and markdown format break characters are escaped to prevent prompt manipulation.

---

## 2. Indian Railway Legal & Ethical Compliance Policy

The Indian Railways (IRCTC) booking ecosystem is protected by strict legal and cyber frameworks (IT Act 2000, Indian Railways Act 1989 Section 143).

`friday.actions.railway_safety.RailwaySafetyCompliance` strictly enforces the following boundaries:

| Prohibited Action | Enforcement Mechanism | Status |
|:---|:---|:---:|
| **Automated CAPTCHA Solving** | Direct code-level block; no OCR/LLM solver integrated | **ENFORCED** |
| **Direct OTP Interception** | Out-of-band user entry only; no SMS snooping | **ENFORCED** |
| **Tatkal Queue Botting** | Strict rate limits; no unauthorized high-frequency scripts | **ENFORCED** |
| **Fake PNR Generation** | All mock PNRs carry `DEMO-TRAIN-` prefix; zero spoofing | **ENFORCED** |
| **Unauthorized Commercial Resale**| No personal-user credential sharing or touting algorithms | **ENFORCED** |

Violations immediately abort execution and raise `ComplianceViolationError`.
