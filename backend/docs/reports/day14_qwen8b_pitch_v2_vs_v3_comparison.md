# Day 14 Qwen3 8B Pitch Correction — v2 vs v3 Comparison

## 1. Summary

This report compares two Qwen3 8B pitch-correction prompt strategies tested on the same 43 selected correction candidates from `day9-maestro-ci-persisted-01-e2e`.

| Version | Strategy | Result |
|---|---|---|
| v2 | Aggressive chromatic-to-diatonic pitch correction | Proposed pitch shifts, but did not improve F1 |
| v3-lite | Local-context conservative correction with fallback | Product-safe behavior, no risky pitch shifts, full coverage |

---

## 2. v2 Result

Prompt v2 allowed pitch correction based on harmonic suspicion and nearby diatonic alternatives.

| Metric | Value |
|---|---:|
| Candidate count | `43` |
| Chunk size | `5` |
| Coverage OK | `true` |
| Proposed pitch shifts | `16` |
| Approved pitch shifts | `14` |
| Rejected pitch shifts | `2` |
| CAR | `0.8750` |
| Applied MIDI mutations | `14` |
| F1 delta | `0.000000` |

### v2 interpretation

v2 successfully proved that the system can complete the full correction loop:

```text
LLM pitch proposal
→ metadata locking
→ pitch safety validation
→ MIDI copy mutation
→ F1 comparison
→ per-correction impact analysis

However, the approved pitch shifts did not improve F1.

The oracle analysis showed:

Oracle result	Count
LLM matches oracle shift	0
LLM shifted but oracle prefers original	10
No nearby safe oracle target	4

This means v2 was safe at the engineering level, but not yet musically effective.

3. v2 Failure Mode

The main v2 failure mode was:

chromatic note in detected key
→ shift to nearby diatonic pitch

The oracle diagnostic showed that this is not valid for real classical music.

Examples:

Candidate	Original	LLM proposed	Oracle
n117	B3 / 59	C4 / 60	B3 / 59
n130	B3 / 59	C4 / 60	B3 / 59
n161	B4 / 71	C5 / 72	B4 / 71
n303	G#3 / 56	A3 / 57	G#3 / 56
n322	D#5 / 75	E5 / 76	D#5 / 75

Key finding:

chromatic note ≠ transcription error
4. v3-lite Result

Prompt v3-lite added local transcription context and used a more conservative decision policy.

Metric	Value
Candidate count	43
Chunk size	1
Chunk count	43
Completed chunks	40
Fallback chunks	3
Failed chunks	0
Locked correction count	43
Coverage OK	true
Keep	8
Flag for review	35
Proposed pitch shifts	0

Fallback candidates:

Candidate ID	Reason
n198	CorrectionBatchValidationError: corrections must be a list
n238	CorrectionBatchValidationError: corrections must be a list
n317	CorrectionBatchValidationError: corrections must be a list
5. v3-lite Interpretation

v3-lite behaves more like a real product system.

Instead of forcing pitch corrections, it uses the following logic:

if local context supports current pitch:
    keep

elif local context is ambiguous:
    flag_for_review

elif LLM output is invalid:
    system fallback → flag_for_review

This avoids the main v2 failure mode:

chromatic → automatically shift to diatonic
6. Product-level Finding

The product should not automatically mutate MIDI simply because a note is harmonically suspicious.

A safer product behavior is:

harmonic suspicion
→ candidate selection
→ local-context LLM review
→ conservative keep / flag_for_review
→ pitch shift only with strong evidence
→ fallback to review on invalid LLM output
7. Scientific Finding

The Day 14 experiments show two different contributions:

v2 contribution

v2 proves that the system can perform real pitch mutation:

14 approved pitch shifts
14 applied to MIDI copy
0 skipped

But v2 does not improve F1:

F1 raw       = 0.048951
F1 corrected = 0.048951
Delta F1     = 0.000000
v3-lite contribution

v3-lite proves product-grade safe LLM behavior:

43/43 candidate coverage
3 invalid LLM outputs handled by fallback
0 unsafe pitch mutations
0 pipeline failures
8. Final Day 14 Conclusion

Day 14 established the full correction loop and identified the correct product direction.

The system can now:

select suspicious notes
ask Qwen3 8B for correction decisions
lock all system metadata
validate coverage
reject unsafe pitch shifts
mutate a MIDI copy
measure F1 before and after correction
analyze per-correction impact
fallback safely when LLM output is invalid

The best current product behavior is not aggressive automatic pitch correction, but conservative local-context review with safe fallback.

9. Next Step

The next step is to create a stronger v4 candidate prompt that supports pitch shifts only when there is stronger production-available evidence, such as:

repeated melodic pattern evidence
neighboring interval consistency
same-note recurrence
local chord context
confidence gap between alternatives

The goal is:

fewer pitch shifts
higher correctness
positive F1 delta

