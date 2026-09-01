# HATO Festival Config — live storefront campaigns, no app updates

**`manifest.json` is what every HATO customer app reads when Grocery opens.**
Edit it → commit → the change is live for all users on their next Grocery visit.

## 🎛️ This repo IS the dashboard

| You want to… | Do this (all in the GitHub web UI) |
|---|---|
| **Publish a festival** | Open a festival file (e.g. `diwali.json`), copy its contents into `manifest.json` → Commit |
| **Edit copy/colors/prices** | Edit `manifest.json` → Commit ("Preview changes" tab first) |
| **Kill the festival NOW** | Set `"enabled": false` in `manifest.json` → Commit |
| **Roll back** | History → pick the last good commit → revert |
| **Audit who changed what** | Commit history is the audit log |

Raw URL served to the app (via `FESTIVAL_MANIFEST_URL` dart-define):

```
https://raw.githubusercontent.com/metavisionrs/hato-festival-config/main/manifest.json
```

## ✅ Safety rails (built into the app)

- Malformed JSON / wrong `schemaVersion` → app silently keeps the **last good cached campaign**, else stock UI. It can never crash the storefront.
- Campaign only shows when `"enabled": true` **and** now is inside `startsAt`–`endsAt` (IST offsets: `+05:30`).
- Validate before committing: paste into any JSON validator, or locally: `python3 -m json.tool manifest.json`.
- ⚠️ Avoid emoji in `banner.title` (renders as "?" on some devices); emoji in tile titles are fine.
- 🚫 Never put secrets here — this repo is public by design (it only holds marketing content).

---

# App-wide platform (schema v2) — operator runbook

Everything below is the NEW two-level platform (build ≥ 48). The v1 flow above
keeps working unchanged for builds 46/47.

## 🧊 FROZEN URLS — never move, rename or reformat

These two raw URLs are hard-coded into builds already in the field. Until the
live campaign ends (**2026-09-06 23:59 IST**) they are read-only; after that
they may be *edited* (v1 publishes) but NEVER moved or renamed:

```
https://raw.githubusercontent.com/metavisionrs/hato-festival-config/main/manifest.json
https://raw.githubusercontent.com/metavisionrs/hato-festival-config/main/krishna_matki.json
```

CI hard-fails any push where either file is missing from the repo root.

## QUICK PUBLISH (v2 flow)

1. Edit the six `sections/*.json` files (copy, blocks, per-section theme).
2. Edit `master_manifest.json`: set `campaignId`, `name`, `startsAt`, `endsAt`,
   global `theme`, and which sections are enabled.
3. **Bump `revision`** in the master and in every section file you touched
   (monotonic int — it is the client cache key; forgetting it = stale clients).
4. Run `python3 tooling/validate.py` locally (or push to a branch and let CI run).
5. Set `"enabled": true` in `master_manifest.json` → commit to `main`. Live.

New v2 clients read (via `FESTIVAL_MASTER_MANIFEST_URL` dart-define):

```
https://raw.githubusercontent.com/metavisionrs/hato-festival-config/main/master_manifest.json
```

## PREVIEW (dev manifest)

`master_manifest.dev.json` is the DEV/simulator entry point — DEV builds point
at it via dart-define. Keep it **identical** to `master_manifest.json` except
`"enabled": true`, so you can see the full campaign on a dev build while
production stays dark. Flip content there first, eyeball it on a simulator,
then mirror to `master_manifest.json`.

## SCHEDULE

- `startsAt` / `endsAt` are ISO-8601 **with explicit IST offset** `+05:30`.
- Active = `enabled && startsAt ≤ now ≤ endsAt && build ≥ minAppBuild`.
- Clients re-evaluate the window on every read — a campaign auto-expires at
  `endsAt` with no commit needed.
- You can commit a fully-built future campaign with `enabled: true` and a
  future `startsAt`; it goes live by itself.

## ROLLBACK

- GitHub → History → find the last good commit → **Revert**. That is the whole
  procedure; raw URLs update within CDN cache time (≤ ~5 min).
- Library files (`janmashtami.json`, `diwali.json`, …) are the curated restore
  points for v1: copy one over `manifest.json` to restore that look.
- ⚠️ **Library-date footgun:** library files carry the dates/ids of the LAST
  campaign they ran. Always update `campaignId`, `startsAt` and `endsAt`
  before publishing a library file — a stale window means the campaign
  silently never shows (or shows with last year's id in analytics).

## KILL SWITCH

| Scope | Action |
|---|---|
| **Whole v2 campaign, every screen** | `master_manifest.json` → `"enabled": false` → commit |
| **One section only** (e.g. ride misbehaves) | `master_manifest.json` → `sections.ride.enabled: false` → commit; the other five keep rendering |
| **Legacy v1 (builds 46/47)** | `manifest.json` → `"enabled": false` → commit |

A section manifest that fails to fetch/parse takes down ONLY that section
(isolation invariant) — but flip its kill switch anyway so clients stop retrying.

## ASSET RULES (policy summary)

All media goes through `RemoteCampaignAsset` (see the app repo's
`docs/festival_platform/REMOTE_ASSET_POLICY.md`):

- **HTTPS only**, host allowlist `raw.githubusercontent.com/metavisionrs/*`.
  Plain-http, other hosts, `data:`/`file:`/script URIs → rejected at parse (and by CI).
- **Size caps:** Lottie ≤ 512 KB · images ≤ 1.5 MB · GIF ≤ 2 MB. Oversize → fallback.
- Types: `lottie | webp | gif | png | jpeg`. **No SVG/Rive** in v2.
- Provide `reducedMotionFallback` for lottie/gif (accessibility); absent →
  static first frame or hidden slot.
- Put new media under `assets/` and reference via `assetBaseUrl` + filename.
- Prices in badges are **display-only marketing copy** — the manifest can never
  carry charging prices, endpoints, auth or feature flags (business-logic firewall).

## SCHEMA (v1 frozen vs v2)

| | v1 (`schemas/campaign.v1.schema.json`) | v2 (`schemas/master-manifest.v2.schema.json` + `schemas/section-manifest.v2.schema.json`) |
|---|---|---|
| Readers | builds 46/47, Grocery only | build ≥ 48, app-wide |
| Entry file | `manifest.json` (FROZEN shape) | `master_manifest.json` → `sections/*.json` |
| Theme | 8 fixed hex colors | 16 optional tokens (`#RRGGBB`), section merges over master |
| Status | **FROZEN — never tighten/extend** | evolving; unknown block types are ignored by clients |

v1→v2 token mapping (from `THEME_TOKENS.md`): `headerColor→header`,
`heroGradientTop→heroGradientStart`, `heroGradientBottom→heroGradientEnd`,
`tileBackground→surface`, `accent→accent`, `titleColor→title`,
`priceBadgeBg→badgeBackground`, `priceBadgeFg→badgeForeground`.

## SUPPORTED SECTIONS

`home`, `food`, `grocery`, `ride`, `parcel`, `carpool` — one
`sections/<name>.json` each; the `"section"` field MUST equal the filename.
A section missing from the master map = stock UI there. Block types per section:

| Section | Blocks |
|---|---|
| grocery | `collectionTile` (v1 parity: title/image/badge{mrp,price}/query/featured) |
| food | `cuisineCollection`, `offerStrip` |
| ride | `destinationShortcut`, `safetyBanner` |
| parcel | `giftIdea`, `boxSizeCard` |
| carpool | `eventRoute`, `emptyStateCopy` |
| home | `promoBanner`, `festivalMessage` |

CTA targets allowlist: `home food grocery ride parcel carpool profile orders support`.
`query` = plain search text, ≤ 64 chars, no URLs. External links are NOT supported.

## LOCALIZATION

Each section manifest carries `copy`: a `locale → { key → string }` map.
`en` is the fallback and must always be present; ship `hi` alongside as the
minimum pair. Blocks reference copy via keys (e.g. `festivalMessage.copyKey`);
a key missing in the user's locale falls back to `en`, then the block hides.
Locale codes: `en`, `hi`, `kn`, `mr`, `ta` (match the app's supported set).

## SPONSOR RULES

- Master `sponsor` = app-wide default strip; a section `hero.sponsor` overrides it.
- `label` (e.g. "POWERED BY") + `name` are required when `enabled: true`;
  always keep a `disclosure` string — sponsored content must be marked.
- `logoUrl` follows ASSET RULES (allowlisted https or `null`).
- Sponsors buy pixels, not behavior: no sponsor value may change prices,
  ranking or navigation beyond the allowlisted CTA targets.

## CI (what validate.yml rejects)

Every push/PR runs `.github/workflows/validate.yml` → `tooling/validate.py`:

1. **Contract guard** — `manifest.json` or `krishna_matki.json` missing at root → FAIL.
2. **Parse** — any `*.json` that isn't valid JSON → FAIL.
3. **Schema** — v1 files vs v1 schema, `master_manifest*.json` vs master v2,
   `sections/*.json` vs section v2 → FAIL on mismatch.
4. **Semantics** — `startsAt ≥ endsAt`, non-`#RRGGBB` colors, badge
   `price > mrp`, empty `campaignId`, `section` ≠ filename → FAIL.
5. **Forbidden patterns** — plaintext-http URLs, any host other than
   `raw.githubusercontent.com/metavisionrs/*`, script URIs, secret-shaped
   tokens (`xox…`, `ghp_…`, `AKIA…`) → FAIL.

Run locally before pushing: `python3 -m pip install jsonschema && python3 tooling/validate.py`.

## COMMON FAILURES

| Symptom | Cause | Fix |
|---|---|---|
| Campaign never appears | `enabled: false`, window not started/expired, or build < `minAppBuild` | Check the three activation conditions |
| Campaign appears but stale | `revision` not bumped | Bump revision in master + changed sections |
| One section is stock UI | Section kill switch off, or its JSON invalid | Check `sections.<s>.enabled` and CI log |
| Published a library file, nothing shows | **Library-date footgun** — stale `startsAt`/`endsAt` | Update `campaignId` + dates before publishing |
| CI: "does not match pattern …raw.githubusercontent…" | Asset/section URL on a foreign host or plain http | Host media in this repo under `assets/` |
| Hero art missing on device | Asset over size cap / decode error | Respect size caps; app degrades silently by design |
| Colors ignored on device | Non-`#RRGGBB` value, or contrast guard tripped | Fix hex; keep text/fill pairs ≥ 3:1 contrast |
| "?" instead of emoji in banner | Emoji in `banner.title` | Keep emoji out of banner titles (tile titles OK) |

## Files

- `manifest.json` — **THE live v1 campaign** (FROZEN URL)
- `master_manifest.json` — v2 production entry point (ships `enabled: false` until activation)
- `master_manifest.dev.json` — v2 DEV/preview entry point (`enabled: true`)
- `sections/` — v2 per-section manifests (home/food/grocery/ride/parcel/carpool)
- `schemas/` — JSON Schemas: `campaign.v1.schema.json` (frozen shape), `master-manifest.v2.schema.json`, `section-manifest.v2.schema.json`
- `tooling/validate.py` — the CI validator (run it locally too)
- `ganeshotsav.json`, `navratri.json`, `diwali.json`, `christmas.json`, `janmashtami.json` — v1 library (janmashtami = current live copy)
- `krishna_matki.json` — Lottie animation (FROZEN URL; hero art via `hero.artUrl` / v2 `RemoteCampaignAsset`)
- `takeover.rfwtxt` — optional remote layout template (RFW); `rfwTemplateUrl` may point at its raw URL (RFW_SECURITY.md applies)
