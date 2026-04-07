---
topic: synapse-audit
created_at: 2026-04-07
updated_at: 2026-04-07
confidence: medium
sources: [bugs.md]
---

# Bug Report: Audit (Risk & Audit)

**Page:** Risk & Audit (`/dashboard/audit`)  
**Date:** 2026-04-07  
**Test Status:** PASS ✅

No bugs found. Page loads correctly with:
- Three status cards: System Integrity (SECURE), Budget Compliance (WARNING), Anomaly Detection (NORMAL)
- "Notification Settings" button
- Active Alerts section with "CLEAR ALL" action
- Alerts visible: "Budget Warning" (10 mins ago), "Rate Limit" (45 mins ago)
- Audit Trail section with "EXPORT CSV" action
- Audit trail table headers: ACTION, ACTOR, TARGET, TIME

Color-coded severity badges working correctly (green SECURE, orange WARNING, blue NORMAL).

![Risk & Audit screenshot](../../test/gateway/screenshots/audit.png)
