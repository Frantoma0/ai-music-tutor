# Day 16 CI Correctable Error Decomposition Report

## 1. Summary

This report extends the Day 15 single-piece correctable-error decomposition to the full 5-piece persisted CI set.

The goal was to test whether the empty correctable ±2 semitone surface observed in the first CI piece was an isolated case or a broader pattern.

Main finding:

```text
Correctable ±2 semitone pitch errors exist in the 5-piece CI set, but they are extremely rare.

Across all 5 persisted CI pieces, only 9 correctable ±2 semitone pitch errors were found among 4689 estimated notes.

Even an oracle correction system that perfectly fixes all of them would improve onset+pitch F1 by only 0.001765.

2. Dataset
Field	Value
Piece count	5
Completed pieces	5
Missing / failed pieces	0
Reference note count	5508
Estimated note count	4689
Onset tolerance	0.05
3. Aggregate Decomposition
Bucket	Count
Already correct TP	3826
Correctable pitch error ≤ 2 semitones	9
Uncorrectable pitch error > 2 semitones	245
Spurious or timing FP	609
Undetected FN	1428
4. Aggregate Onset+Pitch Metric
Metric	Value
Precision	0.815952
Recall	0.694626
F1	0.750417
5. Oracle v4 Ceiling
Field	Value
F1 step per perfect correction	0.000196136
Correctable ±2 errors	9
Oracle v4 gain	0.001765
Oracle v4 F1 ceiling	0.752182

Interpretation:

Even if v4 corrected every correctable ±2 semitone error perfectly, the maximum aggregate F1 gain would be only 0.001765.

This is below the previously used practical no-worse / meaningful-gain threshold of +0.005.

6. Per-Piece Breakdown
#	Composer	Title	TP	Correctable ±2	Uncorrectable >2	Spurious/timing FP	Undetected FN	F1	Oracle gain	Oracle F1
| 1 | Domenico Scarlatti | Sonata K. 525 | `483` | `0` | `33` | `32` | `366` | `0.675524` | `0.000000` | `0.675524` |
| 2 | Domenico Scarlatti | Sonata in D Minor, K. 9 L. 413 | `664` | `3` | `18` | `96` | `175` | `0.809263` | `0.003656` | `0.812919` |
| 3 | Sergei Rachmaninoff | Prelude Op. 32 No. 8 in A Minor | `926` | `0` | `74` | `120` | `400` | `0.734921` | `0.000000` | `0.734921` |
| 4 | Franz Schubert | Impromptu Op. 90 No. 4 in A-flat Major | `838` | `3` | `56` | `154` | `213` | `0.775567` | `0.002776` | `0.778343` |
| 5 | Frédéric Chopin | Etudes Op. 10 Nos. 9 | `915` | `3` | `64` | `207` | `274` | `0.748466` | `0.002454` | `0.750920` |										
7. Key Observations
7.1 Correctable pitch errors are rare

Only 9 correctable ±2 semitone errors were found across 4689 estimated notes.

correctable rate = 0.001919
7.2 Most remaining errors are not addressable by small pitch shifts

The largest non-TP categories are:

spurious/timing FP = 609
undetected FN = 1428
uncorrectable pitch error >2 = 245

These categories are not directly solvable by a ±2 semitone pitch-shift prompt.

7.3 v4 has limited expected impact on this CI set

The result does not prove that v4 is impossible. It shows that, for this 5-piece persisted CI set, the maximum possible F1 improvement from perfect ±2 pitch correction is very small.

8. Product Decision

Prompt v4 should not be treated as the main path to F1 improvement on the current CI set.

The correction pipeline should instead prioritize:

1. safer candidate classification
2. review prioritization
3. distinguishing spurious/timing issues from pitch-correction candidates
4. broader multi-piece validation before investing further in pitch-shift prompting
9. Thesis-Ready Statement

Across the 5-piece persisted CI set, correctable ±2 semitone pitch errors are present but rare: only 9 such errors were found among 4689 estimated notes. Even an oracle correction system that perfectly fixes all of them without introducing new errors would improve onset+pitch F1 by only 0.001765. This indicates that the primary bottleneck is not prompt wording, but the distribution of transcription errors produced by the baseline system.

Bulgarian thesis wording:

В петте CI произведения се наблюдават коригируеми ±2 полутона грешки, но те са много редки — само 9 случая при 4689 оценени ноти. Дори идеален корекционен модул, който поправя всички тези случаи без да въвежда нови грешки, би повишил onset+pitch F1 само с +0.001765. Това показва, че основното ограничение не е формулировката на LLM prompt-а, а разпределението на грешките, генерирани от базовата транскрипционна система.
10. Final Decision

The Day 16 result reframes the correction strategy:

v4 is theoretically possible, but not practically impactful on the current 5-piece CI set.

The next high-value step is to either:

1. run the same decomposition on the 10 formal candidates after producing their output.mid / notes.json artifacts, or
2. focus on review-prioritization and non-pitch correction categories such as spurious/timing false positives.

