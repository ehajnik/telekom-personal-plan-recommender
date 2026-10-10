# Consumer usage profiles (reference)

Typical 12-month monthly means from the PoC synthetic panel (`app_config.yaml` → `model.fixed_centroids`); ranges are the 5th–95th percentile of subscriber means.

| Profile label | Data (GB/month) | Voice (min/month) | SMS/month | Roaming days/month | Notes |
|---------------|-----------------|-------------------|-----------|--------------------|-------|
| **Light / occasional user** | ~4 (1–6) | ~80 (25–140) | ~18 | < 1 | Cost-sensitive, basic smartphone use |
| **Streaming & data-heavy** | ~108 (70–145) | ~290 (155–420) | ~30 | ~2 | Video, social, hotspot |
| **Voice-centric** | ~7 (2–12) | ~1,500 (980–2,100) | ~65 | ~1 | Voice-first, low data |
| **Roaming / travel-heavy** | ~41 (22–62) | ~380 (195–590) | ~45 | ~13 (8–18) | EU and non-EU travel |
| **Broad usage profile** | ~59 (36–82) | ~620 (400–870) | ~117 (67–176) | ~3 | Above-average on every dimension, none dominant |

**Overlays (may combine with any profile; trends in % change per year):**
- **Data appetite growing / shrinking** — data trend ≥ +10 % / ≤ −10 % per year
- **Voice declining → data migration** — voice trend ≤ −10 % per year
- **Roaming increasing** — roaming days up ≥ 2 days/month over the year
- **Mixed profile** — second-closest profile within 1.3× of the closest distance

Legacy names (`Streamer`, `Chatterbox`, `Essential`, `Roamer`, `Messenger`) remain in rule-mode scoring (`PROFILER_MODE=rules`) and tests; the ML/runtime taxonomy uses the labels above.
