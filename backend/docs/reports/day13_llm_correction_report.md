# Day 13 LLM Correction Report

## 1. Summary

| Field | Value |
|---|---:|
| Status | `completed` |
| Model | `qwen3:1.7b` |
| Candidate count | `43` |
| Chunk size | `10` |
| Chunk count | `5` |
| Completed chunks | `5` |
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
| `flag_for_review` | `32` |
| `keep` | `11` |

## 4. Chunk Results

| Chunk | Status | Candidates | Error |
|---:|---|---:|---|
| 1 | `completed` | `10` | `None` |
| 2 | `completed` | `10` | `None` |
| 3 | `completed` | `10` | `None` |
| 4 | `completed` | `10` | `None` |
| 5 | `completed` | `3` | `None` |

## 5. First Locked Corrections

| # | Candidate ID | Action | Pitch | Confidence | HVS | Metadata Source |
|---:|---|---|---|---:|---:|---|
| 1 | `n87` | `flag_for_review` | `B2` | `0.629913` | `0.6` | `system_candidate_locked` |
| 2 | `n117` | `flag_for_review` | `B3` | `0.617295` | `0.6` | `system_candidate_locked` |
| 3 | `n120` | `flag_for_review` | `F#5` | `0.63612` | `0.6` | `system_candidate_locked` |
| 4 | `n127` | `flag_for_review` | `B4` | `0.550604` | `0.6` | `system_candidate_locked` |
| 5 | `n130` | `flag_for_review` | `B3` | `0.608067` | `0.6` | `system_candidate_locked` |
| 6 | `n138` | `flag_for_review` | `B1` | `0.494655` | `0.6` | `system_candidate_locked` |
| 7 | `n142` | `flag_for_review` | `B3` | `0.598731` | `0.6` | `system_candidate_locked` |
| 8 | `n149` | `flag_for_review` | `B1` | `0.432794` | `0.6` | `system_candidate_locked` |
| 9 | `n161` | `flag_for_review` | `B4` | `0.546119` | `0.6` | `system_candidate_locked` |
| 10 | `n172` | `flag_for_review` | `B1` | `0.461883` | `0.6` | `system_candidate_locked` |

## 6. Interpretation

The direct 43-candidate Qwen run failed to produce valid JSON, but chunked processing with chunk size 10 completed successfully.

This confirms that LLM-based correction should be processed in bounded chunks, with schema validation, metadata locking, and coverage validation.

The system does not trust the LLM as a source of numeric metadata. The LLM decides only the correction action and reason, while pitch, timing, confidence, and HVS values are restored from the original system candidates.
