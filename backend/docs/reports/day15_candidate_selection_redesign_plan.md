# Day 15 Candidate Selection Redesign Plan

## 1. Problem

The current HVS + confidence mask selects suspicious notes, but it does not select the actual correctable pitch-error surface.

For the evaluated CI piece:

| Selected candidate bucket | Count |
|---|---:|
| Already correct TP | `36` |
| Spurious or timing FP | `7` |
| Correctable ±2 semitone pitch error | `0` |

This means prompt v4 cannot improve F1 on this piece unless candidate selection is redesigned.

---

## 2. Current Mask Limitation

The current mask is based on:

```text
low confidence + harmonic suspicion

This finds notes that look suspicious harmonically, but Day 15 shows that harmonic suspicion is not the same as a correctable transcription error.

Key finding:

HVS + confidence ≠ correctable pitch-error detector
3. New Selection Target

The next candidate selector should target:

onset-matched estimated notes whose pitch is likely wrong

Instead of:

chromatic or harmonically suspicious notes

The desired target is:

estimated note has onset match
but pitch differs from likely local/reference-free evidence
and possible correction is within ±2 semitones
4. Production-Available Evidence Signals

The new selector should combine multiple signals.

Signal	Purpose
Low Basic Pitch confidence	Estimate may be unreliable
Local repeated pitch pattern	Detect inconsistent note inside repeated motif
Same-pitch recurrence	Detect one outlier among repeated pitch events
Neighbor interval consistency	Detect note that breaks smooth local contour
Local chord compatibility	Weak supporting evidence only
HVS score	Candidate suspicion signal, not correction proof

Important rule:

Harmonic suspicion alone must never trigger automatic pitch mutation.
5. Proposed New Candidate Score

A future candidate score can be structured as:

correctable_candidate_score =
  confidence_uncertainty
+ recurrence_outlier_score
+ interval_inconsistency_score
+ weak_harmonic_support

A note should be selected only if at least two independent signals agree.

6. New Gate Before Prompt v4

Before running prompt v4, the selector must pass this gate:

selected_correctable_count > 0

And ideally:

selected_correctable_rate > current HVS+confidence baseline

Current baseline:

selected_correctable_count = 0 / 43
7. Product Decision

The current product-safe default remains:

v3-lite:
local context + fallback + no unsafe mutation

Prompt v4 should remain blocked until candidate selection can identify actual correctable pitch errors.

8. Next Implementation Step

Implement a deterministic diagnostic selector that labels each estimated note with:

already_correct_tp
correctable_pitch_error_le_2
uncorrectable_pitch_error_gt_2
spurious_or_timing_fp

Then evaluate whether proposed production signals can recover the correctable_pitch_error_le_2 bucket without using reference labels at inference time.
