# Day 14 Qwen3 8B LLM Correction Validation Report

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
| Metadata locked | `true` |
| Coverage OK | `true` |

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
| `keep` | `43` |

## 4. Chunk Results

| Chunk | Status | Candidates | Error |
|---:|---|---:|---|
| 1 | `completed` | `5` | `None` |
| 2 | `completed` | `5` | `None` |
| 3 | `completed` | `5` | `None` |
| 4 | `completed` | `5` | `None` |
| 5 | `completed` | `5` | `None` |
| 6 | `completed` | `5` | `None` |
| 7 | `completed` | `5` | `None` |
| 8 | `completed` | `5` | `None` |
| 9 | `completed` | `3` | `None` |

## 5. First Locked Corrections

| # | Candidate ID | Action | Pitch | Confidence | HVS | Metadata Source |
|---:|---|---|---|---:|---:|---|
| 1 | `n87` | `keep` | `B2` | `0.629913` | `0.6` | `system_candidate_locked` |
| 2 | `n117` | `keep` | `B3` | `0.617295` | `0.6` | `system_candidate_locked` |
| 3 | `n120` | `keep` | `F#5` | `0.63612` | `0.6` | `system_candidate_locked` |
| 4 | `n127` | `keep` | `B4` | `0.550604` | `0.6` | `system_candidate_locked` |
| 5 | `n130` | `keep` | `B3` | `0.608067` | `0.6` | `system_candidate_locked` |
| 6 | `n138` | `keep` | `B1` | `0.494655` | `0.6` | `system_candidate_locked` |
| 7 | `n142` | `keep` | `B3` | `0.598731` | `0.6` | `system_candidate_locked` |
| 8 | `n149` | `keep` | `B1` | `0.432794` | `0.6` | `system_candidate_locked` |
| 9 | `n161` | `keep` | `B4` | `0.546119` | `0.6` | `system_candidate_locked` |
| 10 | `n172` | `keep` | `B1` | `0.461883` | `0.6` | `system_candidate_locked` |

## 6. Interpretation

The direct 43-candidate Qwen3 8B run with chunk size 10 failed coverage validation, but chunked processing with chunk size 5 completed successfully.

This confirms that LLM-based correction should be processed in bounded chunks, with schema validation, metadata locking, and coverage validation.

The system does not trust the LLM as a source of numeric metadata. The LLM decides only the correction action and reason, while pitch, timing, confidence, and HVS values are restored from the original system candidates.
