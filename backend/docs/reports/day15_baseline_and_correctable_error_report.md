# Day 15 Baseline and Correctable Error Diagnostic Report

## 1. Summary

Day 15 diagnosed why the original offset-inclusive F1 score was extremely low and whether a future v4 pitch-correction prompt could realistically improve the evaluated CI piece.

Main finding:

```text
The low 0.048951 F1 score is primarily caused by offset/duration matching.
Under onset+pitch evaluation, the raw transcription reaches 0.675524 F1.
2. Baseline Alignment Diagnosis
Metric	Value
Raw onset+offset+pitch F1	0.048951
Raw onset+pitch precision	0.881387
Raw onset+pitch recall	0.547619
Raw onset+pitch F1	0.675524

The diagnostic harness reproduced the raw production F1:

Field	Value
Expected F1	0.048951
Measured F1	0.048951
Status	MATCH
3. Offset/Duration Finding
Evaluation mode	F1
With offset matching	0.048951
Without offset matching	0.675524

The estimated MIDI has much longer note durations than the MAESTRO reference:

Statistic	Reference	Estimate
Note count	882	548
Median duration	0.045573s	0.186364s
Pitch range	31–89	31–89
Span	65.09s	67.61s

Interpretation:

The transcription is not globally wrong. The low score is mainly caused by offset-inclusive evaluation penalizing longer estimated note durations.
4. Excluded Hypotheses
Hypothesis	Result
Octave mismatch	Not supported
Global transposition	Not supported
Segment mismatch	Not supported
Main bottleneck	Offset/duration matching

Best global pitch shift:

0 semitones
5. v2 Correction Under Primary Metric

Under onset+pitch F1, v2 performs worse than raw.

Metric	Raw	Corrected	Delta
Onset+pitch F1	0.675524	0.661500	-0.014000

No-worse guarantee:

Field	Value
Raw F1	0.675524
No-worse floor	0.670524
Corrected F1	0.661500
Guarantee satisfied	false

Interpretation:

Prompt v2 is useful as mutation-loop proof, but it is not suitable as a product correction policy.
6. Correctable Error Decomposition
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

For this CI piece, there are no correctable ±2 semitone pitch errors. Therefore, prompt v4 cannot improve F1 on this piece using only small pitch shifts.
7. Selected Candidate Overlap

The 43 HVS+confidence selected candidates do not target the correctable error surface.

Selected candidate bucket	Count
Already correct TP	36
Spurious or timing FP	7
Correctable pitch error ≤ 2 semitones	0

Interpretation:

The current HVS+confidence mask selects suspicious notes, but not actual correctable ±2 semitone pitch errors.
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
