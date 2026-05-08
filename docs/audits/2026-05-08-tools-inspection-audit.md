# `tools/inspection/` and `archive/` Audit (2026-05-08)

## tools/inspection/

11 ad-hoc scripts. None are imported from any production code or tests. All compile (parse) cleanly. The only one with a real import-time error is `test_page_inspection.py`.

| File | LOC | Last touched | Compiles | Imports OK | Status |
|---|---|---|---|---|---|
| `debug_track_discovery.py` | 139 | 2025-07-07 | ✅ | ✅ | Probably still useful for debugging track-discovery issues. **Keep.** |
| `inspect_download_button.py` | 233 | 2025-07-07 | ✅ | ✅ | Selectors stale (uses old `.track`, `a.download`). **Update or delete.** |
| `inspect_key_controls.py` | 169 | 2025-07-07 | ✅ | ✅ | Pitch button inspector. Likely still works since pitch UI hasn't changed. **Keep.** |
| `inspect_login_form.py` | 133 | 2025-07-07 | ✅ | ✅ | Login form has changed (now `/my/login.html`). **Update or delete.** |
| `inspect_mixer_after_login.py` | 207 | 2025-07-07 | ✅ | ✅ | Mixer class names have shifted (`.custom__mixer-track-line`). **Update.** |
| `inspect_mixer_controls.py` | 247 | 2025-07-07 | ✅ | ✅ | Same as above. **Update.** |
| `inspect_solo_buttons.py` | 210 | 2025-07-07 | ✅ | ✅ | Solo buttons still work but selectors may need refresh. **Update.** |
| `simple_page_test.py` | 84 | 2025-07-07 | ✅ | ✅ | Generic page-load test. **Keep.** |
| `test_page_inspection.py` | 256 | 2025-07-07 | ✅ | **❌** | `import config` fails — there's no top-level `config.py`. **DELETE — broken.** |
| `verify_login_status.py` | 154 | 2025-07-07 | ✅ | ✅ | Login URL has moved. **Update or delete.** |
| `verify_solo_button_detection.py` | 172 | 2026-05-08 | ✅ | ✅ | Recently updated (Task 6.1). Recent and useful. **Keep.** |

### Recommended actions (for your approval)

- **Delete:** `test_page_inspection.py` (broken at import time, references nonexistent top-level `config`).
- **Keep as-is:** `debug_track_discovery.py`, `inspect_key_controls.py`, `simple_page_test.py`, `verify_solo_button_detection.py` (the recently-updated one).
- **Optional cleanup pass:** the 6 scripts that compile but reference stale selectors (`.track`, `a.download`, old login URL). They'd need refreshes to actually work against the current site. If you don't use them regularly, deleting them is reasonable. If you keep them, they need a selectors update that mirrors the production-code refresh suggested in the Phase 2 findings doc.

## archive/

```
archive/
├── PHASE2_REFACTOR.md  (Phase 2 refactoring plan — looks like completed work)
└── REVIEW.md           (Architecture review document, "Grade: A+")
```

Neither is referenced from current code. Both are historical project documents.

### Recommended actions

- **Keep both** if you want the historical context preserved. They don't cost anything.
- **Delete both** if you'd rather the repo not carry historical planning docs.

This is your call — they're not stale code, just stale docs. CLAUDE.md doesn't speak to non-code historical artifacts.

## What I will NOT delete without your explicit go-ahead

Per the original PLAN.md Task 6.3 ("**Decision time** (ASK USER before deleting)"), I'm presenting findings and stopping. Tell me which of these to delete and I'll do it. Otherwise, the audit completes here.
