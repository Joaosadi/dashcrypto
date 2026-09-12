---
tags:
  - plan
  - mobile
  - responsive
  - dashboard
---

# Mobile Responsiveness Plan

Branch: `mobilechanges` · Base commit: `69b9834`
Goal: make the DashCrypto dashboard usable on phones. Currently the app has zero mobile awareness — it renders desktop grids and fixed-width charts that cram together on narrow screens.

Status: implemented · 2026-09-10 · commits pending on `mobilechanges`

---

## Diagnosis

| # | Problem | Where | Severity |
| --- | --- | --- | --- |
| 1 | Metrics row: 6 columns → ~55px each on a 360px phone; labels/values truncate | [[app.py]]:37 (`st.columns(6)`) | 🔴 |
| 2 | Side-by-side chart grids never stack — every `st.columns(2)` renders two ~170px charts on a phone | [[app.py]]:108, 123, 140, 195, 243 + 211 (6-col histogram grid) | 🔴 |
| 3 | Fixed-width Altair specs: 14 charts hard-code `width=900` (or 600/400), relying on Streamlit's container-stretch | [[plots/btcregressionplots]], [[plots/btcreturns]], [[plots/btcvolatilityplots]], [[plots/macroplots]], [[plots/stablecoinsplot]] | 🟠 |
| 4 | Two charts have **no** width at all (only `height=700`) → Altair 300px default when not overridden | [[plots/btcregressionplots]]:216, 381 | 🟠 |
| 5 | Fixed footer overlays content and fights mobile browser chrome | [[style.css]]:32–43 | 🟡 |
| 6 | Banner typography is desktop-sized (2.2rem h1, 24–32px padding) | [[style.css]]:9–28 | 🟡 |
| 7 | Zero media queries in the stylesheet — CSS cannot respond to viewport | [[style.css]] | 🔴 |
| 8 | No `.streamlit/config.toml`; widgets use Streamlit's default theme, mismatched with the hand-rolled dark CSS; `theme=None` workaround on one chart | [[app.py]]:193 | 🟡 |
| 9 | `use_container_width=True` is deprecated in Streamlit ≥1.49 (`width="stretch"`); requirements only pin `streamlit>=1.30` | [[app.py]], [[requirements.txt]]:2 | 🟡 |

---

## Recommended changes (priority order)

### P1 — Make column grids responsive (fixes #1, #2; highest impact)
- [x] Added breakpoint media queries to [[style.css]] (`stHorizontalBlock` flex-wrap, `stColumn` full-width below 768px)
- [x] Metric rows: 2-up on phones (48%), full-width below 420px; 3-up on tablets (769–1024px) via `:has()`-based rules
- [x] Charts now get the full column width instead of ~170px on phones

### P2 — Standardize chart widths on `width="container"` (fixes #3, #4)
- [x] Replaced all `width=900/600/400` with `width="container"` across the plot modules
- [x] Added explicit `width="container"` to the two `height=700` regression charts
- [x] Migrated render calls from `use_container_width=True` → `width="stretch"` (13 call sites)
- [ ] Optional (deferred): `orient="bottom"` for "Model Traces" legends on narrow screens — kept `right` for now

### P3 — Mobile CSS for chrome elements (fixes #5, #6)
- [x] Footer: `position: static` + `env(safe-area-inset-bottom)` padding on mobile
- [x] Banner: h1 → 1.5rem, reduced padding on small screens
- [x] Added `@media (prefers-reduced-motion)` guard

### P4 — Config hygiene (fixes #8, #9)
- [x] Added `.streamlit/config.toml` dark `[theme]`; dropped the `theme=None` special case
- [x] Bumped `streamlit>=1.49` in [[requirements.txt]]

### P5 — Mobile performance (nice-to-have)
- [x] Added `ttl=300` to `get_snapshot` + `fetch_global_market_metrics` (they were already cached — the TTL bounds staleness instead of caching forever)

---

## Verification plan

- [ ] DevTools responsive mode at 360/390/430px per tab: metrics row, all 2-col pairs, histograms grid, macro dual-axis charts (legend overlap after stacking)
- [ ] `streamlit run app.py` with a narrow window before committing
- [ ] Nothing in this plan touches data logic or the API layer — CSS, chart width specs, config only

---

## Related

- [[index.md]] — project index
- [[app.py]] — layout entry point
- [[style.css]] — all styling (media queries land here)