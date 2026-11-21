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
