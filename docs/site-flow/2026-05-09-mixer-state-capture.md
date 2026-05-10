# Mixer State Capture (verified 2026-05-09)

Every parameter that `karaoke-version.com`'s `basket.php` endpoint
expects is reachable from a single inline `<script>` block on a logged-in
song page. **No UI download click is required to capture them.** This is
the foundation of the direct-API download path
(`packages/download_management/direct_api/session_capture.py`).

## TL;DR

Find the inline script containing `mixer.setLevels(...)`. Regex-extract
everything from its source. Done.

## What basket.php expects

Captured live URL on bryan-adams/18-til-i-die.html (probed 2026-05-08):

```
https://www.karaoke-version.com/basket.php?
  prodid=21279320 &
  s=40852 &
  pannings=1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.10,0.11,-100.12,0.13,0 &
  pitch=0 &
  precount=1 &
  bkac=editf &
  famid=5 &
  method=ajax &
  trackslevels=1,0.2,0.3,100.4,...,0.13,0
```

## Where each param lives in the DOM

The page's inline mixer-init script (single `<script>` block,
identifiable by `mixer.setLevels(`) contains every literal value as
either a `mixer.setX("...")` call or a direct property assignment inside
`mixer.getMixCallback`:

```js
$(document).ready(function () {
    mixer = new Mixer(document.querySelector('.mixer'));
    mixer.setTracksDescription([...]);                      // not used
    mixer.setPrecount("1");                                 // → precount
    mixer.setPitch("0");                                    // → pitch
    mixer.setLevels("1,0.2,0.3,100.4,...,0.13,0");          // → trackslevels TEMPLATE
    mixer.setPannings("1,0.2,0.3,...,-100.12,0.13,0");      // → pannings
    mixer.setStrings({...});                                // not used

    mixer.getMixCallback = function () {
        mixer.parameters.bkac = "editf";                    // → bkac
        mixer.parameters.s = 40852;                         // → s (song id)
        mixer.parameters.prodid = 21279320;                 // → prodid (product id)
        mixer.uri = '/my/begin_download.html?id=21279320&famid=5';
                                                            //   ↑ famid extracted from here
    };
    mixer.editMixCallback = function () { ... };            // not used
    mixer.init('/i/song/i40852/0/multi.json', 214);
});
```

Two of the params we send aren't in the script:
- `method` — always `"ajax"` (hardcoded in our code; the live JS only
  emits this method, never another).
- `trackslevels` (the per-track form) — *built* per track from the
  template using `direct_api.trackslevels.build_trackslevels()`.

## Live JS state vs static script source

The static script source is the *initial* state of the page —
basically a snapshot baked in at page-load time. The live `window.mixer`
object reflects the *current* state, which can diverge from the static
source in two directions:

**Live is incomplete.** `mixer.parameters` at probe time only carries
`{famid, method, precount}` — `prodid`/`s`/`bkac` are only assigned
inside `getMixCallback`, which runs when the user clicks download. For
these params we MUST scrape the static source.

**Live diverges from static for anything UI-mutable.** This is the
tricky case. Any value that can be changed via a UI interaction
(checkbox click, slider drag, dropdown select) updates `window.mixer`
live but does NOT mutate the inline `<script>` source. If we read the
static value, we capture the page's *initial* state, not what the user
has set up. **For UI-mutable params, we MUST read live state.**

Concrete examples seen in the wild:

| Param | UI control | Static value | Live value |
|---|---|---|---|
| `precount` | "Intro count" checkbox | the page's default (often `"0"`) | `"1"` after `ensure_intro_count_enabled` clicks the checkbox |
| `pitch` | key adjustment widget | always `"0"` initially | reflects user's current key choice |
| `pannings` | per-track pan slider | initial pan distribution | post-user-adjustment if anyone moves a slider |

The orchestrator calls `ensure_intro_count_enabled` before
`capture_session`, so the live `precount` is always `"1"` by the time
we capture, but the static script source still says `"0"` for songs
that initialized with the checkbox unchecked. Reading the static value
silently downloaded tracks without a precount click — the
2026-05-09 "no intro click on tracks" bug. Fix:
`session_capture._read_live_precount` reads
`window.mixer.parameters.precount` and overrides the static value.

**Rule of thumb:** if a value can be changed without reloading the
page, read it live. Add a `_read_live_<param>` helper that prefers the
live JS read and falls back to the static value only when the live
read fails.

`mixer.getPannings()` returns the runtime pannings string. Today our
code uses the static `mixer.setPannings("...")` literal because no
codepath touches pan sliders programmatically. If a future feature
auto-pans (e.g. spread mono drums), switch to the live getter.

## Probes used to verify

- `tools/probe_dom_scrape.py` — broad scan for hidden inputs, data-attrs,
  window globals, script regex matches, meta tags.
- `tools/probe_dom_deep.py` — drills into inline scripts, dumps every
  line mentioning `mixer.`, `basket`, `trackslevels`, `bkac`, `pannings`.
- `tools/probe_mixer_state.py` — dumps `window.mixer` keys, parameters,
  pannings, getter return values.
- `tools/probe_script_source.py` — dumps the full inline mixer-init
  script verbatim.

Re-run any of them against a different song's page if you suspect the
site changed.

## When this might break

- Inline script gets minified or split across multiple `<script>`
  blocks → the `mixer.setLevels` marker hunt in `session_capture.py`
  might miss it. **Detect:** `parse_mixer_script` raises `CaptureError`.
  **Recover:** automatic fallback to the legacy Selenium download path
  for that song.
- Site adds a CSRF token to `basket.php` → 403 response.
  **Detect:** `BasketUpdateError` with status 403. **Recover:** legacy
  fallback (and update this doc + the regexes).
- `mixer.parameters.{prodid,s,bkac}` move out of `getMixCallback` →
  could be set inline directly. Update the regexes in
  `session_capture.py` accordingly; the fixture
  `tests/fixtures/mixer_init_script.js` is the canonical example to
  diff against.
