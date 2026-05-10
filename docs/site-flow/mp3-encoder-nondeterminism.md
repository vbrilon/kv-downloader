# MP3 Encoder Nondeterminism (verified 2026-05-08)

**Two server renders of the same song with the same `trackslevels`
produce MP3 files that have identical sizes but different SHA-256s.**
This is a property of the karaoke-version.com server, not a bug in our
code.

## How we found out

While validating Phase 3 of the direct-API rewrite, we wanted to verify
that direct-API output was equivalent to legacy Selenium output. We
compared SHA-256s expecting a match (same trackslevels = same audio =
same bytes). They didn't match.

Hypothesis: direct-API has a subtle bug → wrong trackslevels → different
audio.

Test: run **legacy** twice in a row against the same song. Same params.
Should produce identical bytes if the server is deterministic.

Result:

```
Bass.mp3 — legacy run 1: 752cff40ef4b8779eb2ccd47720928…
Bass.mp3 — legacy run 2: 3e3d7a3af446e629a8c473442a6e49…   (different)
Bass.mp3 — direct-API:   1f8aa263c2a6b88e3ed6126014c8e9…   (different again)
```

All three files: 8,654,285 bytes (identical size). All three played
back as identical-sounding audio.

## What's nondeterministic

Likely candidates inside the rendered MP3:

- ID3v2 tag with a render timestamp
- Encoder-internal state (bit reservoir, dithering RNG)
- LAME-style version/quality string in the tag

Stripping the ID3 prefix and SHA-ing only the MP3 frames also produced
different results, suggesting the encoder itself emits different
bitstreams each run (not just different metadata). We did not dig
further — the audio is correct, that's enough.

## Implications for testing

- **Don't write tests that assert SHA-256 equality across runs.** They
  will be flaky.
- **Do** assert exact size equality. Same trackslevels = same render
  duration = same byte count. This was true across all three runs
  above and is a strict-but-stable check.
- **Do** validate audio content via existing
  `FileManager.validate_audio_content()` (header parsing + sanity).
- The original direct-API "SHA-256-identical" validation gate was
  wrong; size-match was used instead. **Note that size-match is itself
  insufficient for content correctness** — see
  `docs/investigations/2026-05-09-direct-api-mapping-precount-cascade.md`.

## Implications for caching

The CDN URL hash *does* change between renders (it's the cache key for
the rendered MP3). That's what `DirectDownloader._poll_for_fresh_url`
watches for to know the new mix is ready. If the server were
deterministic and the same hash were returned for "same trackslevels =
same MP3", the polling loop would never see a hash flip and would time
out. The nondeterminism is actually load-bearing for our flow.

## Reference

- `tests/fixtures/baseline_sha256.json` — frozen reference for one
  legacy run. Useful as a *size* fixture, not a SHA fixture.
