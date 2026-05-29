# Day 15 Baseline and Correctable Error Diagnostic Report

## 1. Summary

Day 15 diagnosed why the original offset-inclusive F1 score was extremely low and whether a future v4 pitch-correction prompt could realistically improve the evaluated CI piece.

The main finding is that the low `0.048951` F1 score is primarily caused by offset/duration matching, not by a global pitch, octave, transposition, or segment mismatch.

When offset matching is disabled, the raw transcription reaches a much stronger onset+pitch F1 score:

| Metric | Value |
|---|---:|
| Raw onset+offset+pitch F1 | `0.048951` |
| Raw onset+pitch F1 | `0.675524` |
| Raw onset+pitch precision | `0.881387` |
| Raw onset+pitch recall | `0.547619` |

---

## 2. Baseline Reproduction Gate

The raw baseline diagnosis reproduced the previously reported production F1.

| Field | Value |
|---|---:|
| Expected F1 | `0.048951` |
| Measured F1 | `0.048951` |
| Difference | `0.00000005` |
| Status | `MATCH` |

This validates the diagnostic harness for the raw MIDI.

---

## 3. Offset/Duration Finding

The decisive diagnostic result is the offset comparison:

| Evaluation mode | F1 |
|---|---:|
| With offset matching | `0.048951` |
| Without offset matching | `0.675524` |

The estimated MIDI has substantially longer note durations than the MAESTRO reference MIDI:

| Statistic | Reference | Estimate |
|---|---:|---:|
| Note count | `882` | `548` |
| Median duration | `0.045573` | `0.186364` |
| Span seconds | `65.09` | `67.61` |
| Pitch range | `31-89` | `31-89` |

Interpretation:

```text
The low offset-inclusive F1 is primarily caused by duration/offset mismatch.
The raw transcription is much stronger under onset+pitch evaluation than the offset-inclusive score suggests.
4. Excluded Hypotheses

The diagnostics do not support octave, transposition, or segment mismatch as the primary cause.

Check	Result
Best global pitch shift	0 semitones
Best global shift F1	0.048951
Chroma F1	0.055944
Reference first onset	0.908854
Estimate first onset	0.918182

Conclusion:

The piece and segment are aligned, and there is no global octave or transposition mismatch.
5. v2 Correction Under Primary Metric

Using onset+pitch F1 as the primary metric, the v2 corrected MIDI performs worse than the raw MIDI.

Metric	Raw	Corrected	Delta
Onset+pitch precision	0.881387	0.863139	-0.018248
Onset+pitch recall	0.547619	0.536281	-0.011338
Onset+pitch F1	0.675524	0.661538	-0.013986

No-worse guarantee:

Field	Value
Raw F1	0.675524
No-worse floor	0.670524
Corrected F1	0.661538
Guarantee satisfied	false

Interpretation:

Prompt v2 violates the no-worse guarantee under the primary onset+pitch metric.
This confirms that v2 is useful as a mutation-loop proof, but not as a product correction policy.
6. Correctable Error Decomposition

Task B measured how many errors are realistically correctable with a ±2 semitone pitch shift.

Bucket	Count
Already correct TP	483
Correctable pitch error ≤ 2 semitones	0
Uncorrectable pitch error > 2 semitones	33
Spurious or timing FP	32
Undetected FN	366

Oracle v4 ceiling:

Field	Value
F1 step per perfect fix	0.001399
Oracle v4 gain	0.000000
Oracle v4 F1 ceiling	0.675524

Conclusion:

The correctable ±2 semitone pitch-error surface is empty for this CI piece.
Therefore, v4 cannot improve F1 on this piece using only small pitch shifts.
7. Selected Candidate Overlap

The 43 HVS+confidence selected candidates do not overlap with correctable pitch errors.

Selected candidate bucket	Count
| `already_correct_tp` | `36` |
| `spurious_or_timing_fp` | `7` |

Interpretation:

Of the 43 selected candidates, 36 are already true positives and 7 are spurious/timing false positives.
None are correctable ±2 semitone pitch errors.

This shows that the current HVS+confidence mask selects suspicious notes, but not the actual correctable pitch-error surface.

8. Canonical Day 15 Decision

The next step should not be prompt v4 for this CI piece.

The correct direction is:

1. Treat onset+pitch F1 as the primary metric.
2. Treat onset+offset+pitch F1 as a secondary diagnostic metric.
3. Keep v2 as mutation-loop proof only.
4. Keep v3-lite as the product-safe default.
5. Redesign candidate selection before attempting v4 pitch correction.
9. Thesis-ready Statement

The Day 15 diagnostics show that the originally low F1 score is primarily caused by offset/duration matching rather than pitch or onset failure. Under onset+pitch evaluation, the raw transcription reaches 0.675524 F1. However, correctable-error decomposition shows that the selected HVS+confidence candidates contain zero correctable ±2 semitone pitch errors: 36 of the 43 selected candidates are already true positives and 7 are spurious or timing-related false positives. Therefore, the current correction pipeline is safe and traceable, but its candidate-selection signal does not yet target the error surface needed for automatic pitch correction.
