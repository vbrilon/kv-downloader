# karaoke-version.com Download Modal Flow (verified 2026-05-08)

**Method:** Logged in via Chrome DevTools MCP, navigated to a purchased song page (`Don't Bring Me Down` by ELO), installed a `MutationObserver` on `body` watching for class/style/childList changes on any `.modal/.popup/.dialog/.overlay`-matching element, clicked the download button, and observed.

## Answers to Phase 2 questions

1. **Does clicking download open a NEW WINDOW?** No. Inline modal flow only.

2. **CSS selector that matches the readiness modal:** `.modal`, but more precisely the activation signal is `.modal__overlay.is-open` (class is added when the modal becomes "active").

3. **Time from click → modal populated with readiness text:** ~13.9 seconds (this is the server-side mix generation; mostly unavoidable). Click intercepted ⇒ JS click takes <100ms.

4. **Readiness text location:** The exact strings the existing code looks for are present in the populated modal:
   - Heading: `Your download will begin in a moment...`
   - Body: `You can also click on the link below to manually begin your download:`
   - Manual-download link: `<a href="https://c6.recis.io/sl/<HASH>/<HASH>/<filename>.mp3"> Download the file manually</a>`

5. **Modal lifecycle after auto-download fires:** The `.modal` element is **pre-rendered in the DOM from page load** (`visible: true`, but content is empty). When `mixer.getMix()` finishes, the modal's `__overlay` sibling gets the `is-open` class and the `__content` is populated. This means the existing code's `_check_and_handle_inline_popups` is matching `.modal` BEFORE click (when it's empty) and trying to close it — an effectively no-op against the empty pre-render.

6. **Network behavior:** `mixer.getMix()` is a JS function that:
   ```
   this.parameters.trackslevels = this.getLevels();
   this.parameters.pannings    = this.getPannings();
   if (typeof this.getMixCallback === "function") this.getMixCallback();
   this.editMix();
   ```
   `editMix()` makes the backend request that triggers server mix generation. The download URL is delivered into the modal asynchronously when the server is done. We **cannot** bypass the modal trivially via JS — `getMix()` returns void; the URL only appears via the modal.

## Implications for Phase 3 (modal flow rework)

- **`DOWNLOAD_MODAL_COMBINED_SELECTOR` should be `.modal__overlay.is-open, [role='dialog']`**, NOT just `.modal` — because `.modal` is always present, the empty pre-rendered `.modal` would let `_wait_for_download_readiness` return immediately without actual content. The plan's Task 3.1 needs adjustment.
- **The `_check_and_handle_inline_popups` early call at click-time is benign no-op today** (closes the empty pre-rendered modal which has no content) but still costs Selenium round-trips. Move it AFTER readiness detection (Task 3.2 plan was correct).
- **Click-to-modal-readiness is ~14 seconds**, which is server time we can't reduce. The `WebDriverWait` for readiness should have a generous timeout (60s is fine).
- **The readiness text IS reliably in the modal element** (`modal.text` will contain it). No need for `page_source` polling.

## Implications for Phase 8.1 (direct API)

- **Cannot bypass the modal/click flow.** `getMix()` returns void; the download URL only appears asynchronously via the modal DOM.
- **What WE CAN do:** call `driver.execute_script("mixer.getMix();")` directly and skip `a.custom__song-download` click entirely. Already effectively done in Task 1.1 (`js_click_with_scroll` runs `arguments[0].click()`, which fires the onclick `mixer.getMix();return false;`). So further direct-API spike yields nothing meaningful — the existing JS click IS the API call.
- **Phase 8.1: SKIP — not worth pursuing.**

## Implications for Phase 8.3 (Dropbox folder)

- `DOWNLOAD_FOLDER` is `/Users/victorbrilon/Library/CloudStorage/Dropbox/New_Song_Tracks` — a Dropbox-synced folder.
- Every file create / delete (including `shutil.rmtree` in `clear_song_folder`) triggers Dropbox sync events, which can serialize on the cloud-storage daemon.
- Recommendation: change `DOWNLOAD_FOLDER` in `.env` to a local scratch directory (e.g., `~/karaoke-downloads-staging`), then sync/move to Dropbox out-of-band. Cost: minimal — one-line env change + manual move habit. **Phase 8.3: viable, low-risk.**

## Other observations

- **The site's class names have shifted** since the codebase was last updated (`.custom__song-download` for the download link, `.custom__mixer-track-line` for tracks). The codebase still works because of fallback selectors (e.g., `a[class*='download']`). Worth a future selectors refresh, but downloads are succeeding so no urgency.
- **Login URL:** `/login` returns 404; the actual form is at `/my/login.html`. The codebase has `LOGIN_URL = os.getenv("KV_LOGIN_URL", "https://www.karaoke-version.com/login")`. Either Selenium follows a redirect that Chrome MCP doesn't, or this should be updated to `/my/login.html`. **Worth checking** — if Selenium too gets a 404, login is silently failing.

## Captured event log

```
[click @ t=0]
[t=13.9s] MutationObserver: <div class="modal__overlay is-open"> — class attribute added
         At this point, modal__content was populated with the readiness text and download link.
```

(The MutationObserver only caught the overlay class change because the modal content injection happened inside `.modal__content` which did not match the observer's filter — but the snapshot taken immediately after confirmed the populated text.)
