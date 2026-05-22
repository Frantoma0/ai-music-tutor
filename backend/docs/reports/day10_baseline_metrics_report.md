# Day 10 Baseline Metrics Report

> Generated at: `2026-05-22 16:44:56`
> Database: `data/app.sqlite3`
> Job prefix: `day9-maestro-ci-persisted`

## 1. Summary

| Metric | Value |
|---|---:|
| Completed runs | `5/5` |
| Average precision | `0.088185` |
| Average recall | `0.076167` |
| Average F1 | `0.081379` |
| Average overlap | `0.808445` |

## 2. Per-piece metrics

| # | Job ID | Piece | Key | HVS | Precision | Recall | F1 | Overlap | Ref notes | Est notes |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `day9-maestro-ci-persisted-01-e2e` | Domenico Scarlatti — Sonata K. 525 | F major | `0.8065` | `0.063869` | `0.039683` | `0.048951` | `0.859490` | `882` | `548` |
| 2 | `day9-maestro-ci-persisted-02-e2e` | Domenico Scarlatti — Sonata in D Minor, K. 9 L. 413 | D minor | `0.8187` | `0.189501` | `0.172093` | `0.180378` | `0.851847` | `860` | `781` |
| 3 | `day9-maestro-ci-persisted-03-e2e` | Sergei Rachmaninoff — Prelude Op. 32 No. 8 in A Minor | A minor | `0.7991` | `0.058036` | `0.046429` | `0.051587` | `0.707870` | `1400` | `1120` |
| 4 | `day9-maestro-ci-persisted-04-e2e` | Franz Schubert — Impromptu Op. 90 No. 4 in A-flat Major | A- major | `0.8238` | `0.094196` | `0.089189` | `0.091624` | `0.822413` | `1110` | `1051` |
| 5 | `day9-maestro-ci-persisted-05-e2e` | Frédéric Chopin — Etudes Op. 10 Nos. 9 | F minor | `0.8281` | `0.035324` | `0.033439` | `0.034356` | `0.800604` | `1256` | `1189` |

## 3. Interpretation

The baseline scores represent raw Basic Pitch transcription quality before any correction, masking, validation, or HVS-aware repair layer is applied.

The average F1 score is `0.081379`, which should be treated as the initial baseline for later correction experiments.

The average overlap is `0.808445`. This suggests that when note matches are found, their temporal overlap is relatively stronger than the overall note matching rate.

## 4. Traceability

Each metric row is linked to a persisted pipeline run:

```text
metric
→ pipeline_run_id
→ job_id
→ transcription
→ notes/confidence
```

## 5. Metric IDs

| Job ID | Metric ID | Pipeline Run ID |
|---|---|---|
| `day9-maestro-ci-persisted-01-e2e` | `met_680ba813522e` | `run_83945404531b` |
| `day9-maestro-ci-persisted-02-e2e` | `met_ae46f6551a13` | `run_5c76a9618441` |
| `day9-maestro-ci-persisted-03-e2e` | `met_3e7f23508d82` | `run_5de362edefeb` |
| `day9-maestro-ci-persisted-04-e2e` | `met_b791ade27ee1` | `run_fe1c55dd5363` |
| `day9-maestro-ci-persisted-05-e2e` | `met_2d31bc952e3f` | `run_68c57b370cda` |
