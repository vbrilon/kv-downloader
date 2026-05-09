# Site Selectors (Verified Working)

These are the CSS / XPath selectors used against
`karaoke-version.com`. The single source of truth in code is
`packages/configuration/selectors.py` — this doc exists to give a
human-readable inventory grouped by feature.

If a selector breaks, update both places. For DOM-level investigation
(modal open/close behavior, hidden form fields, mixer init script),
also see the other docs in this directory.

## Login

| Element | Selector |
|---|---|
| Email field | `name="frm_login"` |
| Password field | `name="frm_password"` |
| Submit button | `name="sbm"` |

## Tracks

| Element | Selector |
|---|---|
| Track row | `.track[data-index]` |
| Track caption | `.track__caption` |
| Solo button | `button.track__solo` |

## Download

| Element | Selector |
|---|---|
| Download anchor | `a.download` (JavaScript click fallback used to bypass interception) |

## Mixer controls

| Element | Selector |
|---|---|
| Precount checkbox | `#precount` |
| Pitch shift button | `button.btn--pitch.pitch__button` |
| Pitch caption | `.pitch__caption` |
