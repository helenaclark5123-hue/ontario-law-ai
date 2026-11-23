# Ontario Law Assistant: everything that changed since the original build

Written Nov 21, 2026, for making a presentation. Built by a student with no
coding background, by directing Claude Code. Project folder:
`~/Documents/ontario-law-ai`. Live app:
https://ontario-law-ai-hairmdjbph7rmavchjbpbd.streamlit.app/ · Code:
https://github.com/helenaclark5123-hue/ontario-law-ai

## 0. The original assistant (Oct 28): the starting point

A RAG (retrieval-augmented generation) assistant for 3 Ontario laws:
Residential Tenancies Act 2006 (renting), Employment Standards Act 2000
(work), Consumer Protection Act 2002 (buying things). Six stages:

1. Download the laws from the A2AJ Canadian Legal Data dataset (Osgoode Hall / TMU).
2. Split them into 1,189 chunks, one per section (long sections split into parts).
3. Embed the chunks with a free local model (bge-small) into a ChromaDB database.
4. Answer with Claude Haiku using only the 5 retrieved chunks, citing every claim,
   saying "I couldn't find this" when not covered, and adding a legal-information disclaimer.
5. A Streamlit web app.
6. Self-updating: re-download, compare every section, re-embed only changes, log it.
   Proven with a fake amendment (s. 116 changed from 90 to 30 days' notice, then caught and fixed).

## 1. Putting it online (Oct 28-29)

- Deployed on Streamlit Community Cloud; public GitHub repository with a README.
- Swapped PyTorch (626 MB) for FastEmbed: the same search model with identical
  results (tested: 1.0000 agreement), small enough for free cloud servers.
- API key read from Streamlit Secrets online and `.env` locally; never uploaded
  (checked every file and the whole git history).
- Prebuilt search database uploaded, because building it took 3 min 45 s on all
  4 Mac cores and would be far slower on the cloud.
- Problems solved along the way: iCloud was syncing 55,813 library files and
  freezing Python (moved them out of iCloud); the first API key was exposed in
  a screenshot (deleted and replaced); Streamlit kept old code in memory after
  an update (fixed by rebooting the app).

## 2. Better search (Oct 30)

The assistant got 3 test questions wrong because search missed the right section.
Fixed without hard-coding answers:

- **Whole sections:** search in small chunks, but give the AI the whole section,
  so related subsections stay together (ESA s. 13(3) and 13(5)).
- **8 different sections** instead of 5 chunks (two parts of one section no
  longer take two places).
- **Question rewriting:** Claude Haiku rewrites the question into the law's own
  words before searching, and both versions are searched (e.g. "door-to-door"
  becomes "direct agreement", "damage deposit" becomes "security deposit").

| Question | Rank of the right section before | After |
|---|---|---|
| Damage deposit (RTA s. 105) | #35 (missed) | #1 |
| Door-to-door sale (CPA s. 43) | #11 (missed) | #1 |
| Cash register shortage (ESA s. 13) | only half the section | whole section, #1 |
| Rent increase notice (RTA s. 116) | #1 | #1 (nothing broke) |

## 3. The Iterate: a verification layer (Nov 15)

Goal: make the assistant catch its own mistakes, and prove it with numbers.
All new files; the answering code was not changed.

**Part 1: Evaluation (`evaluate.py`, `test_set.csv`).** 22 test questions (7
renting, 7 work, 5 buying, 3 not covered), with answer keys written from the
law text. An AI judge grades each answer correct / wrong / made up.

- Baseline: **20/22 correct (91%), 0% hallucination rate.**
- Both wrong answers were search misses, not made-up law (RTA s. 48.1
  compensation; CPA s. 20, the definition that includes gyms).
- **The judge itself hallucinated:** it marked a correct answer (ESA s. 21,
  unpaid lunch breaks) as "made up" because it trusted its own memory of the
  law. Fixed by giving the judge the law text and telling it not to use memory.

**Part 2: Citation checker (`citations.py`).** It finds every cited section,
checks that it exists, and has an AI judge read the real text to decide
verified / unsupported / not found.

- Caught planted mistakes in a demo (fake "30 days" = unsupported; fake s. 999 = not found).
- Found 2 real legal misstatements inside answers the overall judge called
  "correct" (RTA s. 120: "above the guideline only if the Board orders it";
  RTA s. 83: the eviction test was reversed).
- Improved over 3 versions:

| Version | Real errors caught | False alarms |
|---|---|---|
| First version | 2 | 5 |
| + 2 bug fixes (knows which sections the AI was given; reads the relevant part of long sections) | 1 | 0 |
| + 3-vote majority (the judge gave different answers to the same input) | **2** | **0** |

**Part 3: Semantic entropy confidence score (`entropy.py`).** It generates 5
answers to the same question, groups the ones that mean the same thing, and
calculates entropy: high / medium / low confidence.

- The strict rule (answers must fully entail each other) flagged **90% of
  correct answers** as low confidence, because long legal answers differ in detail.
- Added a looser rule (same conclusion, no contradiction): only 5-10% false
  alarms, but it missed the wrong answer.
- **Key insight:** semantic entropy measures consistency, not correctness. When
  search misses the same section every time, all 5 answers make the same mistake
  and agree.

**Step 7 results (22 questions, both checks on): 21/22 correct, 0 made up, 1 wrong.**

| Check | Caught the wrong answer | Correct answers flagged |
|---|---|---|
| Citation checker (final) | no | 2/21, and both were real misstatements |
| Entropy, strict (low) | yes | 19/21 (90%) |
| Entropy, loose (low) | no | 1/21 (5%) |

**What we learned:**

1. The assistant rarely makes things up (0 made-up answers in 44+ graded
   answers); its mistakes are gaps where search never found a section.
2. Neither check can catch a gap. The citation checker checks what an answer
   says, not what it leaves out; entropy catches inconsistency, not consistent errors.
3. AI judges make mistakes too: one hallucinated, one was inconsistent. Every
   result was checked by hand (`results/manual_review_2026-11-15_full-checks.md`).

**Limitations:** few test questions (35 in the final run); only 1-2 wrong and
0 made-up answers per run, too few to prove a catch rate; the answer key was written by Claude from an
unofficial copy of the law and not yet checked by a person; results vary
between runs (the gym question failed once and passed once).

Cost of the whole Iterate: about $1 in API credit.

## 4. Latest work (Nov 21)

- **13 harder test questions (35 total):** misleading premises ("30 days'
  notice for his daughter"), questions needing two sections, near-miss topics
  (payday loans, debt collectors, tax on tips), and a trap ("What's the
  minimum wage right now?": the law doesn't state today's amount, so the AI
  must not quote one from memory; it passed).
- **Final run (35 questions, final versions of both checks): 33/35 correct
  (94%), 0 made up, 2 wrong.** Easy 11/11, tricky 8/8, hard 8/10, not covered
  6/6 (including all 3 near-miss topics). Both wrong answers were search misses
  (RTA s. 83 retaliation eviction; RTA s. 120 2.5% cap), and the assistant said
  it couldn't find the rule rather than inventing one.

  | Check | Caught a wrong answer | Correct answers flagged |
  |---|---|---|
  | Citation checker | 0/2 | 6/33 (18%) |
  | Entropy, strict (low) | 2/2 | 30/33 (91%) |
  | Entropy, loose (low) | 0/2 | 0/33 |

  Hand review of the citation checker's 7 flags: 1 minor real error, 1
  debatable, 5 false alarms. Longer answers exposed three new weaknesses: the
  judge sees each sentence without its heading; a section number from a
  different Act was mixed up; and the judge sometimes gives its verdict before
  reasoning and then contradicts itself. Details in
  `results/manual_review_2026-11-21_final.md`. The overall conclusions held on
  the bigger, harder test.
- **Fixed those 3 weaknesses** (claim context for the judge, skipping other
  Acts' section numbers, reasoning before the verdict). The targeted false
  alarms disappeared, but re-checking the same answers showed **the judge's
  verdicts on subtle wording change from run to run**: the RTA s. 120 error
  passed this time, and s. 83 was caught by only 1 of 3 judges. Final rule
  (flag when most judges say unsupported): 0 clear false alarms on 57 answers,
  but subtle errors are caught only sometimes. Conclusion: a cheap AI judge
  reliably catches clear citation errors (wrong numbers, sections that don't
  exist) but not subtle misreadings; a stronger judge model is the likely next step.
- **Tried a stronger judge (Claude Sonnet 5.5) on the 16 hand-reviewed answers.**
  It was far more consistent (judges disagreed on 1.5% of citations vs 4% for
  Haiku) and caught the reversed eviction test (RTA s. 83) 3-0, with no false
  alarms. But it still missed 3 of the 4 real errors, every time, reading them
  generously in context. Lesson: a stronger judge fixes inconsistency, not
  coverage, and costs about 20x more.
- **App redesign:** navy and off-white theme, serif headings, law badges,
  example buttons, answer card, works on phones.
- **Chatbot:** people describe their problem in their own words ("my landlord
  is trying to kick me out"); the AI finds the laws that apply, asks a
  plain-English follow-up when a key fact is missing, and understands
  follow-up replies ("he says his daughter is moving in") by turning them into
  a full search question. Every reply has a "Laws used" drop-down with the real
  law text. In testing, the conversation found RTA s. 48.1 (one month's rent
  compensation), which single-question search kept missing.
- The redesign and the chatbot are saved locally; push with GitHub Desktop to
  put them on the live site.

## Files added since the original

| File | What it does |
|---|---|
| `chat.py` | Chat logic: follow-ups, search, plain-language follow-up questions |
| `evaluate.py` | Runs the test set; AI judge grades answers |
| `citations.py` | Citation checker (exists? supported? 3-vote majority) |
| `entropy.py` | Semantic entropy confidence score (strict and loose rules) |
| `compare_checks.py` | Table of what each check caught vs. false alarms |
| `test_set.csv` | 35 test questions with answer keys |
| `results/` | Every run, date-stamped, plus the hand review |

## 5. Two more laws and a new look (Nov 22-23)

- **Website redesign:** three pages (Home, Ask the assistant, How it works)
  with top navigation; dark navy theme with Canadian red, the Canadian flag
  as the logo, and free-licence photos of Toronto and Queen's Park (credited
  on the How it works page). No emojis.
- **Two new laws:** the Occupational Health and Safety Act (workplace safety:
  115 sections) and the Highway Traffic Act (driving: 362 sections). They were
  added with the normal self-updating script: 1,123 new chunks embedded, 0
  changes to the original three laws. The database now holds 5 laws, 1,171
  sections and 2,312 chunks.
- Updated for 5 laws: the question rewriter (new legal-term examples, e.g.
  "unsafe job" becomes "refuse to work where health or safety is in danger"), the
  citation checker (fixed a bug where "Occupational Health and Safety Act"
  citations were dropped as "another Act"), the evaluation and the website.
- **Spot checks:** refusing unsafe work (OHSA s. 43), harassment (OHSA
  s. 32.0.1-32.0.8) and phones while driving (HTA s. 78.1) were all answered
  from the right sections. The speeding question got the fine right
  (s. 128) but missed stunt driving (s. 172), another search gap.
- The test question "What is the speed limit on Ontario highways?" is now
  covered, so its answer key was rewritten: the Act says 50/80 km/h; 100 km/h
  comes from a regulation, a new trap for answering from memory.
  The 33/35 results are from the original three laws; the new laws haven't
  had a full evaluation yet.

## 6. Ontario regulations (Nov 23)

- Added **11 regulations** made under the five Acts, from the A2AJ
  REGULATIONS-ON dataset, using the same pipeline and self-updating (825 new
  chunks; database now 3,137 chunks). Examples: O. Reg. 516/06 (RTA general),
  O. Reg. 288/01 (ESA termination and severance), O. Reg. 17/05 (CPA general),
  O. Reg. 297/13 (mandatory safety training), O. Reg. 339/94 (demerit
  points), O. Reg. 455/07 (stunt driving), Reg. 619 (speed limits: rules
  only, its 99 schedules of highway stretches skipped to avoid noise).
- Each regulation is labelled with its title and parent Act for search, and
  cited by its short name, e.g. (O. Reg. 455/07, s. 3).
- **New capability:** "How many demerit points for speeding?" is now answered
  from O. Reg. 339/94 (6 / 4 / 3 points by how far over).
- **Not fixed:** the stunt-driving rules (O. Reg. 455/07 s. 3, HTA s. 172)
  and the 100/110 km/h limits (Reg. 619 s. 1) are in the database, but are
  usually crowded out of the top 8 by the legal-terms rewrite's results
  (missed in 3 of 3 and 5 of 6 runs). Tested two general fixes, merging
  searches by rank (made the damage-deposit question worse, #1 -> #8) and
  giving the AI 10 sections (no improvement), and kept neither. A better
  search method (e.g. a re-ranking model) is the likely next step.

## 7. Re-ranking search (Nov 23)

- **Problem:** the same question could get a complete answer one run and an
  incomplete one the next, because the legal-terms rewrite varies and the top-8
  sections by similarity score shift with it (e.g. the stunt-driving rules were
  missed in 3 of 3 runs).
- **Fix (`rerank.py`):** gather ~40 candidate sections from both searches, then
  Claude Haiku reads a preview of each and picks the 8 needed to answer (main
  rule, definitions, exceptions, penalties, regulations with the numbers).
  About 0.05 cents and a couple of seconds extra per question.
- **Bug found and fixed while testing:** the AI replied with *law section
  numbers* ("24, 35, 233") instead of the *candidate numbers* asked for, so the
  wrong sections were picked. Candidates are now labelled C1, C2, ... and only
  those labels are read.
- **Measured (13 questions, 3 runs each):** key sections reached the AI
  **39/45 times with re-ranking vs 28/45 before**, with no question doing
  worse. Stunt driving and the 100/110 km/h limits went from 0/3 to 3/3.
- **35-question evaluation:** still 33/35 (94%), 0 made up, but different
  questions pass: the mould-retaliation and lock-change questions are now
  right; the gym question (definition section still hard to find) and public
  holiday pay (right section, but the headline overstated premium pay, an
  answering mistake) were wrong this run. Results vary run to run.
