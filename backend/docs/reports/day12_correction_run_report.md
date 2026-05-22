# Correction Run Report

## 1. Summary

| Field | Value |
|---|---:|
| Correction run ID | `crun_1677fa024972` |
| Job ID | `day9-maestro-ci-persisted-01-e2e` |
| Pipeline run ID | `run_83945404531b` |
| Status | `completed` |
| Note count | `548` |
| Candidate count | `548` |
| Selected count | `43` |
| Mask ratio | `0.0785` |
| Proposal count | `43` |
| Approved count | `43` |
| Rejected count | `0` |
| MIDI mutation allowed | `false` |
| MIDI mutated | `false` |

## 2. Artifact Trace

| Artifact | Path |
|---|---|
| Mask | `artifacts/corrections/day11_e2e_api_mask.json` |
| Proposals | `artifacts/corrections/day11_e2e_api_correct_midi_proposals.json` |
| Validation | `artifacts/corrections/day11_e2e_api_validate_corrections.json` |

## 3. First Proposals

| # | Proposal ID | Candidate ID | Action | Pitch | Confidence | HVS | Status |
|---:|---|---|---|---:|---:|---:|---|
| 1 | `prop_0000` | `n87` | `flag_for_review` | `47` | `0.629913` | `0.6` | `pending_validation` |
| 2 | `prop_0001` | `n117` | `flag_for_review` | `59` | `0.617295` | `0.6` | `pending_validation` |
| 3 | `prop_0002` | `n120` | `flag_for_review` | `78` | `0.63612` | `0.6` | `pending_validation` |
| 4 | `prop_0003` | `n127` | `flag_for_review` | `71` | `0.550604` | `0.6` | `pending_validation` |
| 5 | `prop_0004` | `n130` | `flag_for_review` | `59` | `0.608067` | `0.6` | `pending_validation` |
| 6 | `prop_0005` | `n138` | `flag_for_review` | `35` | `0.494655` | `0.6` | `pending_validation` |
| 7 | `prop_0006` | `n142` | `flag_for_review` | `59` | `0.598731` | `0.6` | `pending_validation` |
| 8 | `prop_0007` | `n149` | `flag_for_review` | `35` | `0.432794` | `0.6` | `pending_validation` |
| 9 | `prop_0008` | `n161` | `flag_for_review` | `71` | `0.546119` | `0.6` | `pending_validation` |
| 10 | `prop_0009` | `n172` | `flag_for_review` | `35` | `0.461883` | `0.6` | `pending_validation` |

## 4. First Validations

| # | Proposal ID | Candidate ID | Status | Approved | Reasons |
|---:|---|---|---|---:|---|
| 1 | `prop_0000` | `n87` | `approved_for_review` | `true` | `none` |
| 2 | `prop_0001` | `n117` | `approved_for_review` | `true` | `none` |
| 3 | `prop_0002` | `n120` | `approved_for_review` | `true` | `none` |
| 4 | `prop_0003` | `n127` | `approved_for_review` | `true` | `none` |
| 5 | `prop_0004` | `n130` | `approved_for_review` | `true` | `none` |
| 6 | `prop_0005` | `n138` | `approved_for_review` | `true` | `none` |
| 7 | `prop_0006` | `n142` | `approved_for_review` | `true` | `none` |
| 8 | `prop_0007` | `n149` | `approved_for_review` | `true` | `none` |
| 9 | `prop_0008` | `n161` | `approved_for_review` | `true` | `none` |
| 10 | `prop_0009` | `n172` | `approved_for_review` | `true` | `none` |

## 5. Interpretation

This correction run represents a safe, non-destructive correction stage. The system generated correction proposals from selected mask candidates, validated them, and preserved the result without mutating MIDI data.

The current behavior is intentionally conservative: proposals are marked as `flag_for_review`, and MIDI mutation remains disabled.
