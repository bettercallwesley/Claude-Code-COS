# Pending Approvals

File-based approval fallback. Scheduled tasks write approval requests here.
Edit `[ ]` to `[Y]` or `[N]` and save. COS checks this file at each session start.

**Format:** `[Y]` = approve, `[N]` = reject, `[ ]` = pending

---

## Validation Notes

- **M365 MCP EMAIL SEND:** NOT AVAILABLE. M365 MCP supports read/search only, not send.
  All approval requests use FILE-BASED FALLBACK (this file) until email send is implemented.

---

## Open Approvals

<!-- Scheduled tasks append approval requests below this line -->


---
## smoke_test — 2026-03-12 08:25
This is a test.

- [ ] **1** — Test item A
- [ ] **2** — Test item B

*Edit `[ ]` to `[Y]` or `[N]` and save. COS checks this file at session start.*
