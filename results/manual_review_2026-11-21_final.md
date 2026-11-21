# Final run: hand review (Nov 21, 2026)

Run: `results/eval_2026-11-21_125426_final.json`: 35 questions (22 original +
13 harder), both checks on, final versions (citation checker with bug fixes and
3-vote majority; entropy with strict and loose rules).

## Grades

**33/35 correct (94%), 0 made up, 2 wrong.**

| Type | Correct |
|---|---|
| easy | 11/11 |
| tricky | 8/8 |
| hard (new) | 8/10 |
| not covered (incl. 3 near-miss topics) | 6/6 |

Both wrong answers were search misses. The assistant honestly said it couldn't
find the rule, and didn't invent one:

- **Eviction for complaining about mould:** RTA s. 83(3)(b) wasn't retrieved;
  the assistant said "those rules aren't in the sections I have".
- **Rent up 10%:** RTA s. 120 (the 2.5% guideline cap) wasn't retrieved; the
  assistant said "probably not" but couldn't state the cap.

The minimum-wage trap passed: the assistant said the law doesn't state today's
amount, instead of quoting a figure from memory. All 3 near-miss topics
(payday loans, debt collectors, tax on tips) correctly got "couldn't find this".

## Checks

| Check | Caught a wrong answer | Correct answers flagged |
|---|---|---|
| Citation checker | 0/2 | 6/33 (18%) |
| Entropy, strict (low) | 2/2 | 30/33 (91%) |
| Entropy, loose (low) | 0/2 | 0/33 (0%) |
| Entropy, loose (low/medium) | 0/2 | 3/33 (9%) |

## The citation checker's 7 flags, checked by hand

| # | Answer | Verdict | Reason |
|---|---|---|---|
| 1 | First and last month's rent (s. 106) | Debatable | "One-month cap" is right for monthly rent; the law says "the lesser of one rent period or one month". |
| 2 | Son moving in (s. 48) | False alarm | "You must give 10 days' notice" was under "Can you leave earlier?", which is the tenant's notice and correct. The judge saw the sentence without its heading. |
| 3 | Son moving in ("s. 2") | False alarm | Citation-finder bug: "s. 2(2)" of a different Act (Fighting Delays, Building Faster Act, 2025) was treated as RTA s. 2. |
| 4 | 13-hour shift (s. 17) | False alarm | "This doesn't apply if a union represents you" referred to the document requirement, which is correct under s. 17(9). Read out of context. |
| 5 | Gym (s. 31) | Minor real error | The one-year term is counted from the day services are available; the answer left that out. |
| 6 | 30 days' notice (s. 48) | False alarm (mostly) | The tenant's 10-day option is correct; only the word "written" isn't in s. 48 itself. |
| 7 | Sick days (s. 50) | False alarm | The judge's own reasoning ends "this should read verified", but it had written "unsupported" first. |

**1 minor real error, 1 debatable, 5 false alarms.** On the 22-question set
(Nov 15) the same checker had 0 false alarms. Longer, harder answers
exposed three new weaknesses:

1. **Missing context:** the judge sees each cited sentence on its own, without
   its heading ("Can you leave earlier?"), so "you" can be misread.
2. **Citations to other laws:** "s. 2(2)" of a different Act was attributed to
   the RTA.
3. **Verdict before reasoning:** the judge writes its label first, then
   sometimes changes its mind in the explanation.

Possible fixes (not done): include the surrounding heading/sentence with each
claim; ignore section numbers that follow another Act's name; ask the judge to
reason first and give the label last.

## Conclusions (same as Nov 15, now on a bigger and harder test)

1. The assistant doesn't make things up: 0 made-up answers in 35. Its mistakes
   are gaps where search never found the key section, and it says so honestly.
2. Neither check catches gaps. The citation checker checks what an answer says,
   not what's missing; entropy measures consistency, and a gap repeats in every sample.
3. Strict entropy flags almost everything (91%); loose entropy flags almost
   nothing (0-9%). Neither separates right from wrong answers here.
4. The citation checker's precision depends on the answers: 0 false alarms on
   the 22-question set, 5 on this run.

## After fixing the 3 weaknesses (re-check of the same saved answers)

Fixes in `citations.py`:
1. Each claim is shown to the judge with its paragraph and heading.
2. Section numbers belonging to another Act (named in the same phrase) are skipped.
3. The judge reasons first and gives its verdict last.

Re-checked files: `eval_2026-11-21_130555_citations-final-checker-nov15.json`
(22 answers) and `eval_2026-11-21_130909_citations-final-checker.json` (35 answers).

**What the fixes solved:** all 5 false alarms they targeted disappeared
(son, 13-hour shift, 30 days' notice, sick-days self-contradiction, the
other-Act "s. 2"); on the 5 answers re-tested, those citations went 3-0 verified.

**What they didn't solve: the judge's verdicts on subtle points change between
runs.** The same answers got different flags than before:

| Flag | Verdict |
|---|---|
| RTA s. 83, no pets (2-1 supported) | real error, missed this time by majority, caught by "disputed" |
| RTA s. 120, rent (3-0 supported) | real error, missed this time by every judge |
| CPA s. 43, door-to-door ("instead" vs "in addition") | minor real error, flagged |
| ESA s. 50.1, sick days | debatable, flagged |
| RTA s. 69, mould eviction ("landlord must apply") | debatable, flagged (on the wrong answer, but not for its real mistake) |
| RTA s. 89, ESA s. 35, CPA s. 43.1, CPA s. 56, ESA s. 57 (each 2-1 supported) | mostly false alarms, "disputed" only |

**Flag rule tried both ways:**
- Flag "disputed" too (any judge objects): caught s. 83, but added ~4 false
  alarms per run. Rejected.
- Flag majority "unsupported" only (final rule): 0 clear false alarms; on the
  35-question run, 3 flags = 1 minor real error, 2 debatable. Missed s. 83 and s. 120.

## Overall conclusion on the citation checker

With the cheapest model (Claude Haiku) as judge, citation checking works for
clear errors (a wrong number, a section that doesn't exist: caught every
time), but is unreliable on subtle legal wording: the same claim can be judged
supported in one run and unsupported in the next, even with 3 votes. Precision
and recall can be traded against each other with the voting rule, but not both
improved. The most likely next step is a stronger judge model, at a higher cost.

## Stronger judge test: Claude Sonnet 5.5 vs Claude Haiku 5.5

Re-checked the 16 answers whose flags I had hand-reviewed, with Sonnet as the
citation judge (3 votes each, same fixed checker): files
`eval_2026-11-21_*_sonnet-judge-nov15.json` and `..._sonnet-judge-final.json`.

| Citation | Hand review | Haiku | Sonnet |
|---|---|---|---|
| RTA s. 83, reversed eviction test | real error | 2-1 supported (disputed) | **0-3 unsupported, caught** |
| RTA s. 120, "only if the Board orders it" | real error | 3-0 supported | 3-0 supported |
| CPA s. 31, gym term | minor real error | 3-0 supported | 3-0 supported |
| CPA s. 43, "instead" vs "in addition" | minor real error | 3-0 supported | 3-0 supported |
| 12 citations judged fine | fine | 0 flagged (3 disputed) | 0 flagged (1 disputed) |
| ESA s. 50.1, RTA s. 69, ESA s. 57 | debatable | 2 flagged, 1 disputed | 0 flagged |

- **Sonnet is far more consistent:** its 3 judges disagreed on 1 of 68
  citations (1.5%), vs 8 of 186 for Haiku (4%).
- **It caught the clearest subtle error** (s. 83) unanimously, which Haiku
  only half-caught.
- **It still missed 3 of 4 real errors, consistently.** On s. 120 it reads
  "only if the Board orders it" generously in the context of the whole answer.
  My hand review counts that as a misstatement; this is a judgment call.
- **It made no clear false alarms,** and it read all 3 debatable cases
  generously.
- **Cost:** about 20x Haiku per word, roughly $1-3 for these 16 answers.

**Conclusion:** a stronger judge mainly fixes *inconsistency* (it gives the
same verdict every time), not *coverage*: it still lets most subtle
misstatements through. Catching those would likely need a different design,
e.g. checking each sentence against the law separately, or a human reviewer
for high-stakes answers.
