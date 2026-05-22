
---

## 2026-05-21 | Basic Pitch confidence extraction implemented

**Supersedes:** 2026-05-21 | Basic Pitch confidence extraction: deferred

**Решение:** T3 `transcribe_audio` вече извлича Basic Pitch note-level confidence от `predict()` note events. Стойността се записва в `notes[].confidence`.

**Пример:** При smoke test `day8-confidence-smoke` беше извлечена стойност `confidence = 0.629446` за нота A4.

**Обосновка:** Basic Pitch `predict()` връща `note_events` във формат `(start, end, pitch, amplitude, pitch_bends)`. Полето `amplitude` се използва като confidence-like score за всяка нота.

**Ефект върху CACSP-HCP:** T5 masking може да използва оригиналната dual-threshold формула:

```text
M(n) = 1 iff confidence < 0.7 AND hvs(n) > 0.6
```

Ако confidence липсва за конкретна нота, системата може да fallback-не към HVS-only masking.

---

## 2026-05-22 | Day 10.5 baseline and mask calibration

**Context:** After Day 9 and Day 10, the system had a persisted 5-piece MAESTRO-derived baseline and a first bridge implementation of correction masking.

### Baseline F1 tolerance sweep

A tolerance sweep was run over the 5 persisted MAESTRO CI pieces using `offset_ratio = 0.2`.

| Onset tolerance | Avg precision | Avg recall | Avg F1 | Avg overlap |
|---:|---:|---:|---:|---:|
| 0.05 | 0.088185 | 0.076167 | 0.081379 | 0.808445 |
| 0.10 | 0.113093 | 0.098218 | 0.104742 | 0.749263 |
| 0.20 | 0.177395 | 0.148599 | 0.160785 | 0.508980 |

**Decision:** The low strict F1 is not explained by onset tolerance alone. Increasing onset tolerance improves F1 only moderately, from `0.081379` at 50ms to `0.160785` at 200ms.

**Interpretation:** Timing sensitivity contributes to the low baseline, but the remaining gap likely comes from synthetic FluidSynth-rendered audio domain mismatch, Basic Pitch behavior on rendered MIDI audio, and transcription segmentation differences.

### Bridge mask threshold sweep

For `day9-maestro-ci-persisted-01-e2e`, the bridge mask used global `hvs_score = 0.8065` and varied only `confidence_threshold`.

| Confidence threshold | Selected notes | Ratio |
|---:|---:|---:|
| 0.5 | 133 / 548 | 0.2427 |
| 0.6 | 261 / 548 | 0.4763 |
| 0.7 | 498 / 548 | 0.9088 |
| 0.8 | 545 / 548 | 0.9945 |

**Decision:** The theoretical `confidence < 0.7` rule is too broad when paired with global HVS bridge logic. Until per-note HVS is implemented, `confidence_threshold = 0.5` is a better experimental bridge setting because it selects about 24% of notes, close to the intended 20–40% correction candidate range.

**Impact on roadmap:** Day 11 should prioritize per-note HVS in `analyze_harmony`. Once per-note HVS is available, the project can re-evaluate whether the original `confidence < 0.7 AND hvs(n) > 0.6` formula becomes selective enough.

