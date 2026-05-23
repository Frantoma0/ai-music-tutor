# Day 14 Qwen3 8B Pitch Correction Report

## 1. Summary

| Field | Value |
|---|---:|
| Status | `completed` |
| Model | `qwen3:8b` |
| Candidate count | `43` |
| Chunk size | `5` |
| Chunk count | `9` |
| Completed chunks | `9` |
| Failed chunks | `0` |
| Locked correction count | `43` |
| Coverage OK | `true` |
| Approved pitch shifts | `14` |
| Rejected pitch shifts | `2` |
| CAR | `0.8750` |

## 2. Coverage

| Field | Value |
|---|---:|
| Expected candidate count | `43` |
| Locked candidate count | `43` |
| Missing candidate IDs | `[]` |
| Duplicate candidate IDs | `[]` |

## 3. Action Distribution

| Action | Count |
|---|---:|
| `flag_for_review` | `26` |
| `keep` | `1` |
| `propose_pitch_shift` | `16` |

## 4. Approved Pitch Shifts

| # | Candidate ID | Original | Proposed | Confidence | HVS | Reason |
|---:|---|---:|---:|---:|---:|---|
| 1 | `n117` | `59` | `60` | `0.617295` | `0.6` | `diatonic in F major` |
| 2 | `n130` | `59` | `60` | `0.608067` | `0.6` | `diatonic in F major` |
| 3 | `n142` | `59` | `60` | `0.598731` | `0.6` | `diatonic in F major` |
| 4 | `n161` | `71` | `72` | `0.546119` | `0.6` | `diatonic in F major` |
| 5 | `n184` | `35` | `36` | `0.464994` | `0.6` | `chromatic note with plausible shift` |
| 6 | `n198` | `59` | `60` | `0.651069` | `0.6` | `chromatic note with plausible shift` |
| 7 | `n206` | `59` | `60` | `0.591822` | `0.6` | `chromatic note with plausible shift` |
| 8 | `n303` | `56` | `57` | `0.508232` | `0.6` | `diatonic in F major` |
| 9 | `n304` | `75` | `76` | `0.368153` | `0.6` | `diatonic in F major` |
| 10 | `n322` | `75` | `76` | `0.528567` | `0.6` | `diatonic in F major` |
| 11 | `n329` | `63` | `64` | `0.296713` | `0.6` | `diatonic in F major` |
| 12 | `n334` | `63` | `62` | `0.599864` | `0.6` | `chromatic note with nearby diatonic option` |
| 13 | `n338` | `63` | `62` | `0.421335` | `0.6` | `chromatic note with nearby diatonic option` |
| 14 | `n516` | `59` | `60` | `0.610165` | `0.6` | `diatonic in F major, nearby pitch with high confidence` |

## 5. Rejected Pitch Shifts

| # | Candidate ID | Original | Proposed | Reasons |
|---:|---|---:|---:|---|
| 1 | `n175` | `71` | `60` | `['pitch_shift_exceeds_safe_limit']` |
| 2 | `n181` | `71` | `60` | `['pitch_shift_exceeds_safe_limit']` |

## 6. Interpretation

This run is the first full-set pitch correction attempt using `qwen3:8b` with JSON mode enabled, chunk size 5, metadata locking, coverage validation, and post-hoc pitch safety validation.

The model proposed concrete pitch shifts instead of only classifying candidates. Unsafe large jumps were rejected by the pitch safety layer before any MIDI mutation.

The reported CAR value measures how many proposed pitch shifts passed deterministic safety constraints. It does not yet prove musical correctness; that requires applying approved corrections to a MIDI copy and measuring corrected F1.
