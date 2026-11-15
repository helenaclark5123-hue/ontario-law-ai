# Hand review of the citation checker's flags

Run: `results/eval_2026-11-15_103929_full-checks.json` (Nov 15, 2026).
The citation checker marked 9 citations "unsupported" in 7 answers. The
answer-level judge graded all 7 answers "correct". I checked each flag
against the law text and against the sections the assistant was given.

| # | Question | Citation | Real error? | What happened |
|---|---|---|---|---|
| 1 | How often can my landlord raise my rent? | RTA s. 120 | **Yes** | Said rent can go above the guideline "only if the Board orders it". s. 120(1) also allows increases by agreement (ss. 121, 123) and under s. 127. |
| 2 | Damage deposit | RTA s. 89 | No | "A separate process, not a deposit" is a fair description; the checker over-read it. |
| 3 | First and last month's rent | RTA s. 120 | No | Cited s. 120 for "the guideline", which s. 120 does set; the timing detail was correctly cited to s. 106(6). |
| 4 | No pets | RTA s. 83 | **Yes** | Reversed the test: s. 83(1)(a) says the Board refuses eviction *unless* satisfied it would be unfair to refuse. The answer said the Board refuses if it would be unfair to grant. |
| 5 | No pets | RTA s. 64 | No | Answer said it didn't have the notice rules (ss. 64-66). True: the assistant wasn't given those sections. The checker looked them up in the database and assumed the assistant had them. |
| 6 | No pets | RTA s. 66 | No | Same as #5. |
| 7 | Overtime | ESA s. 1 | No | "Work week runs Sunday to Saturday if the employer hasn't picked one" is in s. 1, but at character 12,699 of 13,860. The checker only reads the first 6,000 characters of a section. |
| 8 | Notice after 3.5 years | ESA s. 61 | No | Same as #5: the assistant honestly said it wasn't given s. 61, and it wasn't. |
| 9 | Door-to-door | CPA s. 42 | No | Same as #5: the assistant wasn't given s. 42. |

**Result: 2 real errors, 7 false alarms.** Of the 7 flagged answers, 2 (#1, #4)
contain a real misstatement of the law that the answer-level judge didn't
catch, because the main point of the answer was still right. The other 5
answers were flagged only by false alarms.

## Two checker bugs found (not fixed yet)

1. **"I don't have that section" statements.** The checker judges every cited
   section against the full database, so when the assistant honestly says a
   section wasn't in what it was given, the checker calls that unsupported.
   Caused 4 of the 7 false alarms (#5, #6, #8, #9). Fix: tell the checker
   which sections the assistant was actually given.
2. **Long sections get cut off at 6,000 characters.** Caused 1 false alarm
   (#7). Fix: send the part of a long section that matches the claim.

## Other findings from Step 7

- The gym question was graded wrong in the baseline but correct here: this
  time the legal-terms rewrite led search to CPA s. 20 (the definition that
  includes fitness). Search results vary between runs.
- The son question was wrong in both runs for the same reason: search never
  found RTA s. 48.1 (one month's rent compensation).

## After fixing the 2 bugs (re-check of the same saved answers)

Re-checked file: `results/eval_2026-11-15_104642_citations-rechecked.json`.
Fixes: the checker is told which sections the assistant was given, and long
sections show the parts most related to the claim instead of the first
6,000 characters.

| | Before fix | After fix |
|---|---|---|
| Answers flagged | 7 | 1 |
| Pure false alarms (no real error) | 5 | **0** |
| Real errors caught | 2 (#1 s. 120, #4 s. 83) | 1 (#1 s. 120) |

The one remaining flag is real: "above the guideline only if the Board
orders it" misstates s. 120(1). compare_checks.py counts it as a false alarm
only because the answer-level judge graded that answer "correct".

**New finding: the judge is not consistent.** The s. 83 error (#4) was caught
in the 2-question test of the fix, then missed in the full re-check a minute
later: given the same input, the judge read s. 83(1)(a) correctly once and
incorrectly once. A fix would be to ask the judge 3 times and take the
majority, at about 3 times the cost.

## After adding a 3-vote majority (re-check of the same saved answers)

Re-checked file: `results/eval_2026-11-15_105527_citations-majority-vote.json`.
The citation judge is now asked 3 times at once; the majority verdict wins.

| | One judge (after bug fixes) | 3-vote majority |
|---|---|---|
| Answers flagged | 1 | 2 |
| Real errors caught | 1 of 2 (s. 120) | **2 of 2** (s. 120 by 3-0, s. 83 by 2-1) |
| Pure false alarms | 0 | **0** |

The judges split on only 2 of 71 citations, and the majority got both right:
- RTA s. 83 (no pets): 2 unsupported vs 1 verified. Correct: the answer
  reversed the test in s. 83(1)(a).
- ESA s. 13 (cash register): 2 verified vs 1 unsupported. Correct: the claim
  was fine. One judge alone would have raised a false alarm.

compare_checks.py lists the 2 flags as "false alarms (2/21)" only because the
answer-level judge graded both answers "correct" overall. Both contain a real
misstatement of the law.
