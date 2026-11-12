# Harvest: Live3D AI Face Swap → RojSwap

Source: competitive teardown of <https://live3d.io/ai-face-swap>, 2026-11-12 (public pages only, no account, no network probing).
Tags: **CONFIRMED** = seen on a live page or in FaceFusion 3.9.1 source; **INFERRED** = deduced, not proven; **UNPROVEN** = our idea, no run yet.

## Verdict

Live3D wins on distribution, not quality. It is not a better engine than what RojSwap already wraps, and not a usable fallback.

| Fact | Tag |
|------|-----|
| Photo swap free; video swap ≤ 10 s clips, ~3 free/day; images PNG/JPG/WEBP ≤ 20 MB | CONFIRMED |
| Paid = one-time credit packs $10–$200, video ≈ 60 credits/min | CONFIRMED |
| Output "keeps original resolution"; their own FAQ says frontal faces only, big face-shape gaps degrade | CONFIRMED |
| Engine is an inswapper_128-class one-shot swapper (crop → align → swap → paste back) | INFERRED |
| Head / body / character swaps run on resold image-edit models (same credit price as GPT Image 2 / Seedream 5) | INFERRED |
| No visible AI label, no C2PA, no consent step; markets "no watermark" | CONFIRMED |

Why it is not a fallback for us: 10 s cap, no controls, frontal-only, same failure class as our CPU run (sunglasses, profiles, small faces).

## Take (pipeline)

All flags exist in FaceFusion 3.9.1 (checked in source, see PR prover). Queued as `experimental` presets in `pipeline/presets.yaml`; each changes one thing vs an existing preset.

| Preset | Changes vs | Aimed at | Tag |
|--------|-----------|----------|-----|
| `hard_angle` | `identity`: `hyperswap_1a_256` instead of `1c` | head-down / phone frames where glasses stayed | UNPROVEN |
| `identity_codeformer` | `identity`: CodeFormer, `--face-enhancer-weight 0.7` instead of GFPGAN | C3 plastic sheen under red light | UNPROVEN |
| `glasses_region` | `glasses_kept`: BiSeNet parser mask minus `glasses` instead of xseg | blocky xseg lens edge | UNPROVEN |

Knobs worth one grid row each later, not presets yet:

- `--face-swapper-weight` (0–1, default 0.5). In 3.9.1 it blends source and target embeddings: higher = more source identity, lower = closer to target face. Direct C1 lever.
- `--face-swapper-pixel-boost` up to `1024x1024` for hyperswap. Pointless on our 60–120 px faces; matters only on close-ups.
- `--face-enhancer-model restoreformer_plus_plus` — Apache-2.0 restorer, if CodeFormer wins but licence matters.

## Take (process)

- **Pre-flight face check** (UNPROVEN, step 11): before any render, sample frames and report face px size, yaw and detection rate. Live3D only says "use a frontal photo" in an FAQ; we already know 60–120 px faces are our floor. Cheap, local, saves GPU minutes.
- **Refund-on-fail idea → fail fast**: abort a run when detection rate on the short clip is below a threshold instead of rendering garbage.

## Take (compliance) — matters because output goes to social / music / video platforms

| Duty | What we do | Tag |
|------|-----------|-----|
| EU AI Act Art. 50(4), in force 2 Aug 2026: deployers disclose deep fakes; evidently artistic / satirical work gets a lighter "don't hamper the work" disclosure | AI label on every published clip, plus the platform's own altered-content toggle | CONFIRMED (law), UNPROVEN (our flow) |
| US TAKE IT DOWN Act: 48 h removal of non-consensual intimate deepfakes, enforced since 19 May 2026 | Only own or consenting faces; never intimate content. Already a repo rule | CONFIRMED |
| Provenance | Sign the final export with C2PA Content Credentials (`c2patool`, step 10) | UNPROVEN |

Not legal advice; re-check before monetising.

## Licences (FaceFusion 3.9.1 model metadata)

| Model | Licence | Used by |
|-------|---------|---------|
| hyperswap_1a/1b/1c_256 | ResearchRAIL | `identity`, `glasses_kept`, `hard_angle`, `identity_codeformer`, `glasses_region` |
| ghost_1/2/3_256 | Apache-2.0 | `no_glasses`, `no_glasses_region` |
| inswapper_128 | Non-Commercial | — |
| gfpgan_1.4 | Apache-2.0 | `_base` |
| codeformer | S-Lab-1.0 | `identity_codeformer` |
| restoreformer_plus_plus | Apache-2.0 | — |
| xseg_1/2/3 | GPL-3.0 | `glasses_kept` |
| bisenet_resnet_18/34 | MIT | `glasses_region`, `no_glasses_region` |

If a clip is ever monetised, the cleanest stack is ghost + gfpgan / restoreformer++ + bisenet. Hyperswap's ResearchRAIL terms need reading first.

## Skip

- Credit packs, SEO tool-page farm, Telegram / crypto payments — product growth, not pipeline.
- Hosted Live3D as a gate path — strictly worse than local FaceFusion on the RTX 3060.

## Sources

- Live3D pages: [/ai-face-swap](https://live3d.io/ai-face-swap), [/video-face-swap](https://live3d.io/video-face-swap), [/price](https://live3d.io/price), [/acceptable-use-policy](https://live3d.io/acceptable-use-policy)
- FaceFusion 3.9.1 source: `facefusion/processors/modules/face_swapper/{types,core}.py`, `face_enhancer/{types,core}.py`, `facefusion/types.py`, `facefusion/program.py`, `facefusion/face_masker.py` — <https://github.com/facefusion/facefusion/tree/3.9.1>
- EU AI Act Art. 50: <https://artificialintelligenceact.eu/transparency-rules-article-50/>
- FTC, TAKE IT DOWN Act enforcement: <https://www.ftc.gov/business-guidance/blog/2026/05/take-it-down-act-enforcement-starts-now-what-know-about-ftc-tida>
- C2PA tooling: <https://opensource.contentauthenticity.org/>
