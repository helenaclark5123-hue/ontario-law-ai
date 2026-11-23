# Prompt for Claude Code: turn the Ontario Law Assistant into The Bridge

Read this whole file before doing anything. Then look through the project (app.py, views/, ui.py, answer.py, chat.py, search.py, citations.py, entropy.py, run_tests.py, evaluate.py, README.md, CHANGES_SUMMARY.md) so you understand what already exists. **Do not write any code yet.** First send me a short plan: what you'll change, in what order, and any questions. Wait for my OK.

---

## 1. What The Bridge is (the vision)

The Bridge is my startup idea. Always call it **"The Bridge"** (never just "Bridge").

**The problem:** Most people with a legal problem never get help. Lawyers are expensive, legal aid is underfunded, people don't know their rights, and the whole process feels scary and isolating. Most legal tech is American, cold and clinical. So people with a bad landlord, an unpaid paycheque or a store that won't give a refund usually just give up.

**What The Bridge does:** It helps everyday people in Ontario understand their rights and take action, in plain, warm language, grounded in the real text of the law. **We are not replacing lawyers. We're making sure people show up ready.**

**Mission line:** "You deserve justice. We help you get there."

**Who it's for first:** Young people (18–30), especially students, who've hit an unfair situation (landlord, employer, a purchase gone wrong) and can't afford a lawyer.

**The three pillars:**
1. **Legal navigation.** Plain-language explanations of your situation, your rights and your options, always citing the exact law.
2. **Emotional support.** Legal problems are stressful. The Bridge sounds like a knowledgeable friend, not a legal form. It acknowledges that this is hard.
3. **Community.** "You're not the first person to go through this." (Long term. See the note in section 4.)

**What makes it different:** warm and human, built for Canadian (Ontario) law, answers come from the actual law and not from AI memory, and it covers everything from small consumer complaints to serious problems.

**The golden rule (legal safety):** The Bridge gives legal **information**, never legal **advice**.
- Never: "You should file a complaint."
- Always: "The law says X." and "People in this situation typically have these options: ..."
This is the same approach CLEO / Steps to Justice uses in Ontario.

---

## 2. What already exists. Don't break it.

The app is a working Streamlit site (home page, chat assistant, How it works page) with:
- RAG over 30+ Ontario Acts and their main regulations (data/, db/), from the A2AJ dataset
- Query rewriting plus Claude Haiku re-ranking (search.py, rerank.py)
- Answers only from the retrieved sections, with a citation for every point, "I couldn't find this" when the law doesn't cover it, and follow-up questions when a key fact is missing
- A verification layer: AI-judge evaluation, a citation checker (citations.py), and a semantic entropy confidence score (entropy.py), which comes from my research paper
- Self-updating laws (update_laws.py)
- A test set with results: 33/35 correct, 0 made-up laws, 6/6 out-of-scope questions declined

**Keep the tech stack as it is.** My old business plan mentions LangChain, Pinecone, the CanLII API and Bubble. Ignore those; the current stack works and is tested.

---

## 3. Changes to make, in priority order

### A. Rebrand to The Bridge
- Rename the site to **The Bridge**, with a subtitle along the lines of "Know your rights in Ontario. In plain language, from the real law."
- Add the mission line on the home page.
- Keep the current visual design unless a change clearly fits the warmer brand. If you think it should change, ask me first.

### B. Warmer, emotion-first tone (system prompt in answer.py / chat.py)
- Open with one short, genuine acknowledgment when someone describes a stressful situation (e.g. "That sounds really stressful. Here's what the law says."). No fake cheerfulness, and no long sympathy paragraphs.
- Plain language, short sentences, no legal jargon without explaining it.
- Enforce the golden rule: describe what the law says and the options people typically have. Never tell the user what they *should* do.
- Answer in the user's language if they write in another language. Say that the law text and citations are in English and that the translation is unofficial.
- **After changing the prompt, rerun the test set (run_tests.py / evaluate.py) and show me the before/after numbers.** The tone change must not lower accuracy or add made-up law.

### C. "What you can do next" (navigation)
After the legal explanation, add a short **Options people in your situation typically have** section that points to the right body or next step for the topic, for example:
- Renting: Landlord and Tenant Board
- Work: an Employment Standards claim with the Ministry of Labour
- Buying: a Consumer Protection Ontario complaint
- Small Claims Court, a community legal clinic, etc.

Only include a body or form if the retrieved law or a verified official page supports it. **Every link must be a real official URL that you have checked. Show me the list before using it.**

### D. Use the confidence score to know when to send people to a human
- When the semantic entropy score says the answer is uncertain, or the question is about something serious, show a clear, kind box: "This one is worth talking to a professional about," with free help options.
- Always escalate (give the law information if covered, but strongly point to a lawyer or clinic) for: criminal charges, immigration and refugee matters, anything with a court date already scheduled, and immediate safety situations. For immediate danger, point to emergency services (911) first.
- **Decision for me:** my original plan said "never answer child custody or family law," but the app now covers family law and custody Acts. Ask me how I want to handle this before changing anything.

### E. Free legal help directory
Add a section (on How it works, or its own page) listing free and low-cost legal help in Ontario, such as Legal Aid Ontario, community legal clinics, Steps to Justice (CLEO), the Law Society Referral Service, and student legal clinics (e.g. at Osgoode, U of T, Queen's). **Verify every name and URL from the official site. Don't guess. Show me the list before adding it.**

### F. "Get ready for a lawyer" summary (the "show up ready" feature)
A button in the chat that turns the conversation into a one-page summary the user can download:
- what happened (in their words)
- the laws that apply (with sections)
- their options
- questions to ask a lawyer or clinic

Keep it as information, not advice.

### G. Flag a wrong answer
Add a small "Flag this answer" button on each answer that logs the question, the answer and an optional comment (to a file in logs/ for now). Mention it on How it works as part of how accuracy is maintained.

### H. Update the How it works page
Rewrite it to tell The Bridge story while keeping the technical honesty:
1. Why The Bridge exists (short)
2. Information, not advice: what that means and why it matters
3. How an answer is made (keep the current three steps)
4. **How The Bridge checks itself.** Explain the AI judge, the citation checker and the semantic entropy score ("it asks itself the same question 5 times; if the answers disagree, it's probably guessing") in plain words.
5. Test results (keep the real numbers exactly as they are)
6. Keeping the law current
7. Where to get more help (the directory from E)
8. Limitations (keep them)

---

## 4. Not now (don't build these)
- **Community forum:** Streamlit can't safely host a moderated, anonymous forum right now. At most, add a "Coming soon: a community where people share what worked for them" note, and ask me before adding even that.
- Premium tier, payments, user accounts, lawyer marketplace, B2B features.
- Email signups: if you want a waitlist, ask me. I'd link to a Google Form I make rather than store emails in the app.

---

## 5. Rules for working on this
- **Don't invent facts or numbers.** Don't put statistics on the site (like "14 million Canadians...") unless I give you a source. Keep test results exactly as they are in results/.
- **No fake testimonials or made-up user stories.** Example scenarios must be clearly labelled as examples.
- Keep "This is legal information, not legal advice" visible on every page.
- Work in small steps. After each step, run the app locally, check it works, run the tests if the answer pipeline changed, and commit with a clear message.
- Update README.md and CHANGES_SUMMARY.md at the end.
- If anything in this file conflicts with what the code actually does, tell me instead of guessing.
