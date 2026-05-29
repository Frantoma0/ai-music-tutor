# Day 15 All-Note Rule Evaluation

## 1. Summary

This report evaluates simple production-available rules against all 548 estimated notes.

The target class is:

```text
spurious_or_timing_fp

The goal is to test whether confidence, duration, local overlap, and interval context can identify notes that should be reviewed as spurious/timing issues rather than sent to pitch correction.

2. Target Distribution
Bucket	Count
Already correct TP	483
Spurious or timing FP	32
Uncorrectable pitch error > 2 semitones	33
Correctable pitch error ≤ 2 semitones	0

The target class contains:

32 spurious_or_timing_fp notes
3. Rule Performance
Rule	Hits	TP	FP	FN	Precision	Recall	F1
confidence < 0.50	133	24	109	8	0.1805	0.7500	0.2909
duration > 0.19	269	23	246	9	0.0855	0.7188	0.1528
overlap_count >= 4	67	12	55	20	0.1791	0.3750	0.2424
abs_prev_interval >= 12	204	17	187	15	0.0833	0.5312	0.1441
confidence < 0.50 AND overlap_count >= 4	23	11	12	21	0.4783	0.3438	0.4000
three_signal_rule	56	16	40	16	0.2857	0.5000	0.3636
4. Best Rule So Far

The best rule by F1 and precision is:

confidence < 0.50 AND overlap_count >= 4

Result:

Metric	Value
Hits	23
True positives	11
False positives	12
False negatives	21
Precision	0.4783
Recall	0.3438
F1	0.4000
5. Interpretation

The rule is useful, but not product-grade.

It is a better signal than HVS alone for identifying spurious/timing false positives, but it still produces many false positives when evaluated across all 548 notes.

Therefore:

confidence < 0.50 AND overlap_count >= 4

should be treated as a review signal, not as an automatic correction trigger.

6. Product Decision

The system should separate note candidates into different review types:

pitch-correction candidate
spurious/timing candidate
already-plausible note

The current rule helps with the second category:

spurious/timing candidate detection

It does not solve:

correctable pitch-error detection

because the evaluated CI piece contains zero correctable ±2 semitone pitch errors.

7. Canonical Finding

Low confidence combined with high local overlap is the best simple signal found so far for spurious/timing false positives, but its all-note precision is only 0.4783. This means it is useful for prioritizing review, but insufficient for automatic correction.

8. Next Step

The next step should test stronger composite features across all notes, such as:

confidence percentile
duration percentile
overlap density
local chord density
repeated pitch behavior
melodic outlier score
onset neighborhood ambiguity

The goal is to improve precision before using any signal in the product correction loop.
