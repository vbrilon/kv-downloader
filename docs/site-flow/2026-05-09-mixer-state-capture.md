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

`mixer.parameters` (live state) only carries `{famid, method, precount}`
at probe time — `prodid`/`s`/`bkac` are only assigned inside
`getMixCallback`, which runs when download is clicked. So **live state
is incomplete**; the static script source is the complete reference.

`mixer.getPannings()` returns the runtime pannings string. That's
useful when you want the post-user-adjustment pannings, but for the
default-pannings case, the `mixer.setPannings("...")` literal in the
script source is identical and easier to extract.

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
