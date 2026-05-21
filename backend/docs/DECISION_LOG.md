
---

## 2026-05-21 | Basic Pitch confidence extraction implemented

**Supersedes:** 2026-05-21 | Basic Pitch confidence extraction: deferred

**Решение:** T3 `transcribe_audio` вече извлича Basic Pitch note-level confidence от `predict()` note events. Стойността се записва в `notes[].confidence`.

**Пример:** При smoke test `day8-confidence-smoke` беше извлечена стойност `confidence = 0.629446` за нота A4.

**Обосновка:** Basic Pitch `predict()` връща `note_events` във формат `(start, end, pitch, amplitude, pitch_bends)`. Полето `amplitude` се използва като confidence-like score за всяка нота.

**Ефект върху CACSP-HCP:** T5 masking може да използва оригиналната dual-threshold формула:

```text
M(n) = 1 iff confidence < 0.7 AND hvs(n) > 0.6

Ако confidence липсва за конкретна нота, системата може да fallback-не към HVS-only masking.
