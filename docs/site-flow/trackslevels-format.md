# `trackslevels` Format Reference

The `trackslevels` query-param on `basket.php` tells the server which
tracks to mix at which volumes. Format verified 2026-05-08 against
`bryan-adams/18-til-i-die`. Code: `packages/download_management/direct_api/trackslevels.py`.

## Wire format

Comma-separated segments, one per slot. Two kinds:

| Shape | Meaning |
|---|---|
| `<level>.<id>` | A track slot. `level` ∈ 0..100 (volume %), `id` is the server-side track id (NOT the data-index). |
| `<bare-number>` | A *flag* slot — leading `1` is the precount-enabled flag, trailing `0` is currently unknown but server-required. |

Example template captured for an 18-Til-I-Die page (13 audible
tracks):

```
1,0.2,0.3,100.4,0.5,0.6,0.7,0.8,0.9,0.10,0.11,0.12,0.13,0
^ ^^^ ^^^ ^^^^^                                       ^^^^ ^
│ │   │   │                                           │    │
│ │   │   │                                           │    └ trailing edge (bare; leave alone)
│ │   │   │                                           └ pos 12, id=13, level=0
│ │   │   └ pos 3, id=4, level=100  (Drum Kit was seeded soloed when captured)
│ │   └ pos 2, id=3, level=0
│ └ pos 1, id=2, level=0
└ pos 0: precount flag (bare; leave alone)
```

So this 14-slot template encodes 12 audible tracks (positions 1..12)
plus 2 flag slots (positions 0 and 13).

## ⚠️ Critical: bare-numeric slots

**Do NOT change bare-numeric slots.** `basket.php` runs a server-side
consistency check; modifying position 0 or position N-1 returns HTTP
500. Verified empirically (`tools/probe_direct_api.py`).
`build_trackslevels()` enforces this:

- Asks for a soloable position; refuses `target_pos=0` or
  `target_pos=N-1` with `InvalidPositionError`.
- Always emits the bare slots verbatim from the template.

## Position ↔ data-index mapping

For a song with N audible tracks (data-index 0 = the click/precount
synthetic track, data-index 1..N-1 = real tracks):

| data-index | trackslevels position | id |
|---|---|---|
| 0 (Click) | (none — handled via `precount=1`) | (none) |
| 1 (first real track) | 1 | 2 |
| 2 | 2 | 3 |
| … | … | … |
| N-1 (last real track) | N-1 | N |

So **`target_pos == data_index`** for non-click tracks.

## Soloing the click track

The click track (data-index 0) is rendered by setting **all** `.id`
slots to `0.<id>` while keeping the `precount=1` template param. This
gives the server "no instruments selected, but precount enabled" — the
server returns a click-only mix.

In code:

```python
# orchestrator dispatches click track to:
downloader.download_track(target_pos=1, dest=dest, level=0)
# build_trackslevels produces all-zero levels except for "0.2" at pos 1,
# which is the same as every other slot — net effect = silence + click.
```

## Soloing a real track

```python
# data-index 3 (e.g. Bass) → target_pos=3, level=100
build_trackslevels(template, target_pos=3, level=100)
# → "1,0.2,0.3,100.4,0.5,...,0.13,0"   (only pos 3 has level=100)
```

The function:

1. Parses the template into segments.
2. Validates `target_pos` is a real-track slot.
3. Emits each segment verbatim (bare slots), or with `level=requested`
   at the target, or with `level=0` everywhere else.

## Reference test fixture

`tests/fixtures/mixer_init_script.js` contains the verbatim inline
script that produced the example template above. The template lives on
the line:

```js
mixer.setLevels("1,0.2,0.3,100.4,0.5,0.6,0.7,0.8,0.9,0.10,0.11,0.12,0.13,0");
```

If you suspect the format changed, re-run `tools/probe_script_source.py`
against a song page and diff the output against this fixture.
