# Day 15 Evidence Signal Audit

## 1. Summary

This report documents the first evidence-signal audit after the Day 15 correctable-error decomposition.

The goal was to understand whether production-available signals can distinguish useful correction candidates from already-correct notes or spurious/timing false positives.

Main finding:

```text
The current HVS + confidence mask does not identify correctable ±2 semitone pitch errors.
However, low confidence combined with high local overlap is a strong signal for spurious/timing false positives.
2. Available Fields

The transcription note artifact contains:

id
pitch / pitch_name
start / end / duration
velocity
confidence
instrument information

The correction mask artifact contains:

id
pitch / pitch_name
start / end
confidence
hvs_score
selected
reason

All 548 candidates contain the required fields:

Field	Present	Non-null
id	548	548
pitch	548	548
start	548	548
end	548	548
confidence	548	548
hvs_score	548	548
selected	548	548
3. Selected Candidate Buckets

The 43 selected candidates were previously classified as:

Bucket	Count
Already correct TP	36
Spurious or timing FP	7
Correctable ±2 semitone pitch error	0

This confirms that the current HVS + confidence selector does not target the correctable pitch-error surface.

4. Selected Candidate Feature Audit
Already-correct true positives
Feature	Value
Count	36
Confidence mean	0.596474
Confidence median	0.607625
HVS mean	0.600000
Duration mean	0.177967
Duration median	0.152273
Spurious/timing false positives
Feature	Value
Count	7
Confidence mean	0.420075
Confidence median	0.432794
HVS mean	0.600000
Duration mean	0.269481
Duration median	0.277273

Interpretation:

HVS score does not distinguish already-correct notes from spurious/timing false positives.
Both groups have HVS mean = 0.6.

More useful signals are:

lower confidence
longer duration
5. Local Context Audit
Already-correct true positives
Feature	Mean	Median
Nearby count	3.777778	4.000000
Overlap count	2.027778	2.000000
Absolute previous interval	7.916667	4.000000
Absolute next interval	1.888889	0.000000
Duration	0.177967	0.152273
Confidence	0.596474	0.607625
Spurious/timing false positives
Feature	Mean	Median
Nearby count	4.571429	5.000000
Overlap count	3.571429	4.000000
Absolute previous interval	16.857143	17.000000
Absolute next interval	5.000000	0.000000
Duration	0.269481	0.277273
Confidence	0.420075	0.432794

Interpretation:

Spurious/timing false positives tend to have lower confidence, longer duration, more overlapping notes, and larger previous interval jumps.
6. Threshold Rule Audit

Several simple threshold rules were evaluated on the 43 selected candidates.

Rule	Total hits	Spurious hits	Already-correct hits
confidence < 0.50	10	7 / 7	3 / 36
duration > 0.19	17	7 / 7	10 / 36
overlap_count >= 4	8	5 / 7	3 / 36
abs_prev_interval >= 12	11	4 / 7	7 / 36
confidence < 0.50 AND duration > 0.19	9	7 / 7	2 / 36
confidence < 0.50 AND overlap_count >= 4	5	5 / 7	0 / 36
confidence < 0.50 AND abs_prev_interval >= 12	5	4 / 7	1 / 36
Three-signal rule	7	6 / 7	1 / 36
7. Best Rule So Far

The best conservative rule is:

confidence < 0.50 AND overlap_count >= 4

Result:

Metric	Value
Total hits	5
Spurious/timing hits	5 / 7
Already-correct hits	0 / 36
Precision for spurious/timing	100%
Recall for spurious/timing	71.4%

This rule is not a pitch-correction selector. It is a spurious/timing filter.

8. Product Interpretation

The new evidence does not yet support automatic pitch correction.

Instead, it supports a safer product behavior:

low confidence + high local overlap
→ likely spurious/timing issue
→ flag for review
→ do not send to pitch-shift mutation

This protects the system from applying pitch correction to notes that are not pitch-correction candidates.

9. Candidate Selection Implication

The current selector:

low confidence + high HVS

should not be used directly as a pitch-correction selector.

A better pipeline should separate candidate types:

1. pitch-correction candidates
2. spurious/timing candidates
3. already-plausible notes

The current evidence supports the second category:

spurious/timing candidate detection

not yet the first:

correctable pitch-error detection
10. Canonical Finding
Local overlap + low confidence is a better indicator of spurious/timing false positives than HVS alone.

The current HVS score remains useful as a suspicion signal, but it is not sufficient to identify correctable pitch errors.

11. Next Step

The next implementation step should be a deterministic evidence-audit script that computes these features for all 548 notes, not only the 43 selected candidates.

It should output:

candidate_id
bucket label
confidence
duration
hvs_score
overlap_count
nearby_count
previous interval
next interval
selection status
rule hits

This will allow the project to test whether simple production-available features can improve candidate selection before designing prompt v4.
