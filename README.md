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

## Files

- `manifest.json` — **THE live campaign**
- `ganeshotsav.json`, `navratri.json`, `diwali.json`, `christmas.json`, `janmashtami.json` — ready-made library
- `krishna_matki.json` — Lottie animation (hero art via `hero.artUrl` + `"artIsLottie": true`)
- `takeover.rfwtxt` — optional remote layout template (RFW); point `rfwTemplateUrl` at its raw URL to override the takeover layout entirely

## Schema (v1) quick reference

See `janmashtami.json` for a full example: `theme` (8 hex colors), `hero`
(kicker/title/artUrl/artIsLottie/sponsor), `banner` (title/subtitle/ctaLabel),
`festivalTab` (label/isNew), `searchHints[]`, `collections[]`
(title/imageUrl/badge{mrp,price}/query/featured — first `featured:true` tile
renders double-height). Full docs live in the app repo:
`docs/festival/FESTIVAL_CAMPAIGNS.md`.
