# Loom demo: the self-updating twist (about 2 minutes)

Tested on Oct 28, 2026. Each step below worked in a full rehearsal.

## Before you hit record

1. Start the app in Terminal (leave this window open while recording):

   ```
   cd ~/Documents/ontario-law-ai && .venv/bin/streamlit run app.py --server.address localhost
   ```

2. Open http://localhost:8501 in your browser. Wait until the question box appears (about 15 seconds the first time).
3. Close the TextEdit window with your `.env` file, and anything else that shows your API key.
4. Open a second Terminal window and type `cd ~/Documents/ontario-law-ai` so it's ready for step 3.

## Recording

**Step 1: the real law.** Ask:

> How much notice does my landlord need to give before raising my rent?

It answers **90 days** and cites s. 116. Open the **s. 116** box to show the real law text.

Say something like: "Every claim cites the exact section, and I can open the real law text underneath."

**Step 2: fake an amendment.** In the second Terminal window, run:

```
.venv/bin/python fake_amendment.py
```

Say: "This pretends the law changed. It edits my stored copy of section 116 to say 30 days instead of 90."

**Step 3: the app follows the stored law.** Ask the same question again. It now says **30 days**, and the s. 116 box shows "30 days" too.

Say: "My app trusts the law text it's given, not its own memory. So if the stored law is out of date, so are the answers. That's why it needs to update itself."

**Step 4: check for updates.** Open the sidebar (the » arrow at the top left) and click **Check for updates** *once*. Wait about 20 seconds until the box appears; don't click again while it's spinning.

It should say **"Updated: 1 changed"** and **"Changed: Residential Tenancies Act, 2006, s. 116"**.

Say: "It re-downloaded the three laws, compared all 1,189 sections, and found that only section 116 no longer matches. It re-embedded just that one section."

**Step 5: fixed.** Ask the question once more. It's back to **90 days**.

**Optional:** open `logs/update_log.md` to show the before and after text the update recorded.

## If something goes wrong

- **It says "No changes" in step 4:** the button was probably clicked twice. The sidebar's "Last change found" line still shows s. 116 was fixed. Ask the question to confirm it's back to 90 days.
- **Step 2 says "already faked":** an earlier test wasn't fixed yet. Click **Check for updates** first, then start again.
